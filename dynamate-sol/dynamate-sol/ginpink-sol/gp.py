#!/usr/bin/python
import os
from pathlib import Path
import sys
import time
import argparse
import logging
import pickle
import json
import re
import multiprocessing

from solidity_parser_util import (
    parse_solidity,
    extract_solidity_methods,
    extract_require_statements,
    extract_assert_statements,
)
from ginpink import *

# IMPORTANT: This is where the Solidity contracts are read from
SOLIDITY_CONTRACTS_DIR = os.environ.get(
    "INVSOL_THEORIES_DIR",
    str(Path.home() / "dynamate-sol" / "theories"),
).rstrip("/") + "/"
EXTENSION = ".sol"          # solidity contracts
THEORY_INFO_EXT = ".info"   # theory metadata files


class PlainPrinter:
    def __init__(self, name, iteration):
        self.name = name
        self.iteration = iteration

    def printout(self, message):
        print(message)

    def done(self):
        pass


class FilePrinter(PlainPrinter):
    def __init__(self, name, iteration):
        super().__init__(name, iteration)
        version = 1
        while True:
            filename = f"{self.name}.iteration_{self.iteration}.v{version}.txt"
            if not os.path.exists(filename):
                self.file = open(filename, "w")
                break
            version += 1

    def printout(self, message):
        self.file.write(message + "\n")

    def done(self):
        self.file.close()


class MutationTracker:
    def __init__(self, method_name, expected_invariants):
        self.method_name = method_name
        self.iterations = []
        self.all_mutations = set()
        self.expected_invariants = set(expected_invariants)
        self.cur_iteration = 0
        self.commands = []
        self.generated = []
        self.outcome = []
        self.times = []
        self.found_invariants = []

    def new_iteration(self, commands):
        self.cur_iteration += 1
        self.iterations.append(set())
        self.commands.append(commands)
        self.outcome.append(None)
        self.found_invariants.append(set())
        self.times.append(None)
        self.generated.append(None)

    def new_mutations(self, mutations, generated):
        news = set(mutations) - self.all_mutations
        self.all_mutations.update(news)
        self.iterations[self.cur_iteration - 1] = news
        self.outcome[self.cur_iteration - 1] = len(news)
        self.found_invariants[self.cur_iteration - 1] = set(
            [n for n in news if n in self.expected_invariants]
        )
        self.generated[self.cur_iteration - 1] = generated
        return news

    def has_found_all(self):
        return self.expected_invariants.issubset(self.all_mutations)

    def save_progress(self, filename):
        with open(filename, "wb") as f:
            pickle.dump(self, f)


# ----------------------- helper functions for filtering -----------------------


def extract_identifiers(formula):
    """
    Extract identifier-like tokens from a formula string.
    This is intentionally simple: it just finds word-like tokens
    starting with a letter or underscore.
    """
    if not formula:
        return set()
    candidates = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", formula)
    blacklist = {
        "true",
        "false",
        "for",
        "if",
        "else",
        "while",
        "return",
        "require",
        "assert",
        "mapping",
        "uint",
        "int",
        "address",
        "bool",
        "this",
        "msg",
        "memory",
        "storage",
        "calldata",
        "public",
        "private",
        "internal",
        "external",
        "view",
        "pure",
        "payable",
        "returns",
        "contract",
        "function",
        "struct",
    }
    return {tok for tok in candidates if tok not in blacklist}


def extract_allowed_vars(postconditions, invariants):
    """
    Build the set of 'allowed' variables from pre/postconditions and
    expected invariants. We then require each candidate mutation to
    mention at least one of these variables (to kill constant-only junk).
    """
    allowed = set()
    for pred in postconditions:
        allowed |= extract_identifiers(pred)
    for inv in invariants:
        allowed |= extract_identifiers(inv)
    return allowed


def strip_outer_parens(s):
    """
    Strip outer matching parentheses repeatedly.
    Very simple: assumes formulas are not crazy-nested with mismatched parens.
    """
    if not s:
        return s
    s = s.strip()
    changed = True
    while changed and len(s) >= 2 and s[0] == "(" and s[-1] == ")":
        depth = 0
        balanced = True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    balanced = False
                    break
        if balanced:
            s = s[1:-1].strip()
        else:
            changed = False
    return s.strip()


def normalize_pred(p):
    """
    Normalize a predicate string for simple equality / negation checks.
    """
    if not p:
        return p
    p = strip_outer_parens(p)
    return re.sub(r"\s+", "", p)


def is_trivial_implication(expr):
    """
    Detect trivial / junk implications of the form:
      - P ==> P
      - P ==> !P
      - !P ==> P
      - !P ==> !P
    """
    m = re.match(r"^\s*(.+?)\s*==>\s*(.+?)\s*$", expr)
    if not m:
        return False

    lhs_raw, rhs_raw = m.group(1), m.group(2)
    lhs = normalize_pred(lhs_raw)
    rhs = normalize_pred(rhs_raw)

    if not lhs or not rhs:
        return False

    if lhs == rhs:
        return True

    if lhs.startswith("!") and lhs[1:] == rhs:
        return True
    if rhs.startswith("!") and rhs[1:] == lhs:
        return True

    return False



def _unparse_mutation(node) -> str:
    """
    Render a mutation node back to Solidity source.

    Falling back to repr() emits the node class name, so a perfectly good
    candidate is reported as BinaryExpression(n <= maxN) and is neither valid
    Solidity nor usable by the verifier.
    """
    for attribute in ("to_solidity", "to_source", "unparse", "render"):
        method = getattr(node, attribute, None)
        if callable(method):
            try:
                text = method()
                if isinstance(text, str) and text.strip():
                    return text.strip()
            except Exception:
                pass

    for attribute in ("expr", "expression", "source", "text", "code"):
        value = getattr(node, attribute, None)
        if isinstance(value, str) and value.strip():
            return value.strip()

    text = str(node).strip()
    opened = text.find("(")
    if opened > 0 and text.endswith(")") and text[:opened].isidentifier():
        inner = text[opened + 1 : -1].strip()
        if inner:
            return inner
    return text


MUTATION_CHARS = re.compile(r"^[A-Za-z0-9_()\[\].,\s><=!&|+\-/*%]+$")
RELATIONAL_OP = re.compile(r"(==>|<=|>=|==|!=|<|>|&&|\|\|)")
BARE_ASSIGNMENT = re.compile(r"(?<![<>=!])=(?!=)")
DANGLING_MEMBER = re.compile(r"\.\s*(?![A-Za-z_])")


def wellformed_reason(mutation):
    """
    Why a candidate cannot be used, or an empty string when it is usable.

    Member access and indexing are part of the invariant language the paper
    describes: arr.length bounds a traversal and balances[i] >= 0 is the
    quantifier-instantiation example in Table 2. Rejecting every expression
    containing a dot or a bracket would discard exactly those, so the check
    here is structural rather than a character whitelist.
    """
    text = (mutation or "").strip()
    if not text:
        return "empty"
    if not MUTATION_CHARS.match(text):
        return "unexpected characters"
    if not RELATIONAL_OP.search(text):
        return "no relational operator"
    if BARE_ASSIGNMENT.search(text):
        return "assignment rather than a comparison"
    if DANGLING_MEMBER.search(text):
        return "incomplete member access"
    if "[]" in text:
        return "empty index"

    stack = []
    closing = {")": "(", "]": "["}
    for character in text:
        if character in "([":
            stack.append(character)
        elif character in ")]":
            if not stack or stack.pop() != closing[character]:
                return "unbalanced brackets"
    if stack:
        return "unbalanced brackets"

    return ""


def executable_forms(mutations, debug=False, strict=False, allowed_vars=None):
    """
    Filter the raw mutation strings into 'executable' and semantically
    non-trivial candidates.
    """
    exec_mutations = []
    for mutation in mutations:
        if not isinstance(mutation, (str, bytes)):
            mutation = _unparse_mutation(mutation)

        if debug:
            logging.debug(f"Computing executable form of: {mutation}")

        reason = wellformed_reason(mutation)
        if reason:
            print(f"[FILTERED - {reason}] {mutation}")
            continue

        if strict and is_trivial_implication(mutation):
            print(f"[FILTERED - trivial implication] {mutation}")
            continue

        if strict and allowed_vars:
            if not any(
                re.search(r"\b" + re.escape(v) + r"\b", mutation)
                for v in allowed_vars
            ):
                print(f"[FILTERED - no allowed vars] {mutation}")
                continue

        if strict and re.match(r"^\s*(true|false|x\s*==\s*x)\s*$", mutation):
            print(f"[FILTERED - strict rule] {mutation}")
            continue

        exec_mutations.append(mutation)

    return exec_mutations


def process_commandsequence(command_sequence, mutator, debug=False):
    """
    Run a single command sequence against the mutator and collect mutations.
    """
    mutations = []
    print(f"[CHILD DEBUG] Starting command sequence: {command_sequence}")

    for cmd in command_sequence:
        if hasattr(mutator, cmd):
            method = getattr(mutator, cmd)
            print(f"[CHILD DEBUG] Executing mutator method: {cmd}")
            try:
                generated = method()
                print(
                    f"[CHILD DEBUG] Method '{cmd}' generated {len(generated)} mutations."
                )
                mutations.extend(generated)
                for m in generated:
                    print(f"[CHILD RAW MUTATION] {m}")
            except Exception as e:
                print(f"[CHILD ERROR] Exception during '{cmd}': {e}")
        else:
            print(f"[CHILD WARNING] Mutator has no method named '{cmd}'")

    print(f"[CHILD RETURNING] Total mutations: {len(mutations)}")
    return mutations


class _MethodAdapter:
    """
    Minimal object that looks like SolPinkMethod to SolidityMutator.
    This avoids the crash: SolidityMutator expects method.get_ints/get_bools/get_refs.
    """
    def __init__(self, ints=None, bools=None, refs=None):
        self._ints = ints or []
        self._bools = bools or []
        self._refs = refs or []
        self.arity = 0

    def get_ints(self):
        return self._ints

    def get_bools(self):
        return self._bools

    def get_refs(self):
        return self._refs

    def set_arity(self, n):
        self.arity = n


def _loop_methods_from_sidecar(contract):
    """
    Loop-bearing methods as recorded by the AST Analyzer.

    The analyzer parses with solc, so it copes with syntax the third-party
    Solidity parser does not, such as call{value: x}("") assigned into a tuple
    with a hole. When the sidecar is present it is preferred.
    """
    path = os.path.join(SOLIDITY_CONTRACTS_DIR, contract + ".methods.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"[WARN] Could not read {path}: {exc}")
        return {}
    return {name: list(funcs) for name, funcs in loaded.items() if funcs}


def _parse_posts_to_ast(postconditions):
    """
    Convert list[str] -> list[AST expr] using qp() if available.
    Returns list of parsed AST nodes (best-effort).
    """
    posts_ast = []
    for p in postconditions:
        try:
            e = qp(p.strip().rstrip(";"))
            if e is not None:
                posts_ast.append(e)
        except Exception:
            pass
    return posts_ast


def _best_effort_seed_method(contract_code, function_name):
    """
    Try to build some seed ints/bools/refs for the mutator using ginpink helpers if present.
    This is best-effort: if helpers are missing or parsing fails, seeds are empty.
    """
    int_seeds = []
    bool_seeds = []
    ref_seeds = []

    # ints
    try:
        if "extract_integer_expressions" in globals():
            for s in extract_integer_expressions(contract_code, function_name) or []:
                try:
                    e = qp(str(s).strip().rstrip(";"))
                    if e is not None:
                        int_seeds.append(e)
                except Exception:
                    pass
    except Exception:
        pass

    # bools
    try:
        if "extract_boolean_expressions" in globals():
            raw = extract_boolean_expressions(contract_code, function_name) or []
            for s in raw:
                # sometimes extractor returns tuples
                if isinstance(s, tuple):
                    for part in s:
                        if part:
                            try:
                                e = qp(str(part).strip().rstrip(";"))
                                if e is not None:
                                    bool_seeds.append(e)
                            except Exception:
                                pass
                else:
                    if s:
                        try:
                            e = qp(str(s).strip().rstrip(";"))
                            if e is not None:
                                bool_seeds.append(e)
                        except Exception:
                            pass
    except Exception:
        pass

    # refs
    try:
        if "extract_references" in globals():
            refs = extract_references(contract_code, function_name) or []
            for r in refs:
                if isinstance(r, tuple):
                    for x in r:
                        if x:
                            ref_seeds.append(str(x))
                else:
                    if r:
                        ref_seeds.append(str(r))
    except Exception:
        pass

    return _MethodAdapter(ints=int_seeds, bools=bool_seeds, refs=ref_seeds)



DEFAULT_STRATEGIES = [
    "variable_substitution_mutations",
    "constraint_relaxation_mutations",
    "boundary_adjustment_mutations",
    "quantifier_instantiation_mutations",
    "conditional_splitting_mutations",
]

STRATEGY_ALIASES = {
    "variable_substitution": "variable_substitution_mutations",
    "constraint_relaxation": "constraint_relaxation_mutations",
    "boundary_adjustment": "boundary_adjustment_mutations",
    "quantifier_instantiation": "quantifier_instantiation_mutations",
    "conditional_splitting": "conditional_splitting_mutations",
}


def _resolve_command_sequences(special, method):
    """
    Decide which mutation strategies to run for a method.

    An explicit --cmd wins. Otherwise the theory file may name the strategies in
    its Commands section. Falling back to a single generic pass would exercise
    only one of the five strategies the evaluation reports on.
    """
    if special:
        return special

    declared = getattr(method, "commands", None) or []
    sequences = []
    for entry in declared:
        if isinstance(entry, str):
            parts = [c.strip() for c in entry.split(";") if c.strip()]
        else:
            parts = [str(c).strip() for c in entry if str(c).strip()]
        parts = [STRATEGY_ALIASES.get(c, c) for c in parts]
        if parts:
            sequences.append(parts)

    if sequences:
        return sequences

    return [[name] for name in DEFAULT_STRATEGIES]


def process_method(
    method_name,
    method_obj,
    posts_ast,
    postconditions,
    invariants,
    theories,
    debug=False,
    timeout=60,
    print_to_file=True,
    special=None,
    strict=True,
):
    """
    Run mutation generation for a single method.

    NOTE: this version does NOT use multiprocessing. It calls
    process_commandsequence directly so all logging is visible and
    we can debug why iteration files might be empty.
    """
    print(f"[PM] >>> ENTER process_method({method_name})")

    tracker = MutationTracker(method_name, invariants)
    printer = (
        FilePrinter(method_name, tracker.cur_iteration)
        if print_to_file
        else PlainPrinter(method_name, tracker.cur_iteration)
    )

    allowed_vars = extract_allowed_vars(postconditions, invariants)
    command_sequences = _resolve_command_sequences(special, method_obj)

    print(
        f"[PM] method={method_name}: "
        f"#post={len(postconditions)}, #inv={len(invariants)}, "
        f"#allowed_vars={len(allowed_vars)}, "
        f"command_sequences={command_sequences}"
    )

    strategy_record = {}

    for commands in command_sequences:
        print(f"[PM] Top of loop for method={method_name}, commands={commands}")
        strategy = "; ".join(c.replace("_mutations", "") for c in commands)

        # Only early-stop if we actually have expected invariants.
        if tracker.expected_invariants and tracker.has_found_all():
            print(f"[PM] tracker.has_found_all() is True, breaking out for {method_name}")
            break

        tracker.new_iteration("; ".join(commands))

        # FIX: correct SolidityMutator init args:
        # SolidityMutator(method_obj, theories_list, posts_ast)
        mutator = SolidityMutator(method_obj, list(theories.values()), posts_ast)
        print(f"[PM] Created SolidityMutator for {method_name}, now calling process_commandsequence")

        # 🔁 Run synchronously
        try:
            mutations = process_commandsequence(commands, mutator, debug)
            print(
                f"[PM] process_commandsequence returned {type(mutations)} "
                f"of len={len(mutations) if mutations is not None else 'None'}"
            )
        except Exception as e:
            print(f"[ERROR] Exception in process_commandsequence for {method_name}: {e}")
            mutations = []

        if mutations:
            mutations = set(mutations)
            print(f"[PM] mutations set has size={len(mutations)}")

            # Log raw mutations
            for m in mutations:
                printer.printout(f"[RAW MUTATION] {m}")
                print(f"[RAW MUTATION] {m}")

            executable_mutations = executable_forms(
                mutations,
                debug=debug,
                strict=strict,
                allowed_vars=allowed_vars,
            )

            print(f"[PM] executable_mutations size={len(executable_mutations)}")

            tracker.new_mutations(executable_mutations, len(mutations))

            for m in executable_mutations:
                printer.printout(f"[MUTATION] {m}")
                print(f"[MUTATION] {m}")

            strategy_record[strategy] = {
                "raw": len(mutations),
                "candidates": len(executable_mutations),
                "mutations": sorted(str(m) for m in executable_mutations),
            }

            printer.printout(
                f"✅ Strategy {'; '.join(commands)} generated {len(executable_mutations)} mutations."
            )
        else:
            strategy_record[strategy] = {"raw": 0, "candidates": 0, "mutations": []}
            printer.printout("⚠️ No mutations generated (empty result).")
            print(f"[PM] ⚠️ No mutations returned for {method_name} with commands {commands}.")

        tracker.save_progress(f"{method_name}.pkl")
        print(f"[PM] Saved tracker progress for {method_name} to {method_name}.pkl")

    with open(f"{method_name}.strategies.json", "w", encoding="utf-8") as handle:
        json.dump(
            {"method": method_name, "strategies": strategy_record},
            handle,
            indent=2,
        )
    print(
        f"[PM] Strategy tally for {method_name}: "
        + ", ".join(f"{k}={v['candidates']}" for k, v in strategy_record.items())
    )

    printer.done()
    print(f"[PM] <<< LEAVE process_method({method_name})")
    return tracker


def _register_theory(theories: dict, theory_contract_name: str, theory_obj):
    """
    Store a theory object under both:
      - 'T<Contract>' (the theory contract name)
      - '<Contract>' (base contract name)
    so that later lookup by base name succeeds.
    """
    theories[theory_contract_name] = theory_obj
    if theory_contract_name.startswith("T") and len(theory_contract_name) > 1:
        base = theory_contract_name[1:]
        if base:
            theories[base] = theory_obj


def _get_theory_for_contract(theories: dict, contract_name: str):
    """
    Robust lookup: try base name and 'T'+base name.
    """
    if contract_name in theories:
        return theories[contract_name]
    tname = "T" + contract_name
    if tname in theories:
        return theories[tname]
    return None


def get_methods_and_theories(contract_names, theory_dir):
    """
    Discover methods + theories for the given contract names.
    """
    methods = []
    theories = {}

    print(f"[DEBUG] get_methods_and_theories: contract_names={contract_names}, theory_dir={theory_dir}")
    print(f"[DEBUG] SOLIDITY_CONTRACTS_DIR={SOLIDITY_CONTRACTS_DIR}")

    # FIX #1: Load theory info files T*.info (not T*.sol)
    for fname in os.listdir(theory_dir):
        if fname.startswith("T") and fname.endswith(THEORY_INFO_EXT):
            theory_contract_name = fname[: -len(THEORY_INFO_EXT)]  # strip ".info"
            try:
                # IMPORTANT: your ginpink.read_contract MUST read .info files.
                # If your read_contract still uses EXTENSION=".sol", fix it in ginpink.py.
                theory_obj = read_contract(theory_contract_name, theory_dir)
                _register_theory(theories, theory_contract_name, theory_obj)
                try:
                    print(
                        f"[DEBUG] Loaded theory info for {theory_contract_name} "
                        f"with #bools={len(theory_obj.get_bools())}"
                    )
                except Exception:
                    print(f"[DEBUG] Loaded theory info for {theory_contract_name}")
            except Exception as e:
                print(f"❌ Failed to read theory info file {fname}: {e}")

    # Load main Solidity contracts
    for contract in contract_names:
        contract_path = os.path.join(SOLIDITY_CONTRACTS_DIR, contract + EXTENSION)
        print(f"[DEBUG] Reading Solidity contract from {contract_path}")
        if not os.path.exists(contract_path):
            print(f"[WARN] Solidity contract not found at {contract_path}")
            continue

        with open(contract_path, "r") as f:
            contract_code = f.read()

        extracted = _loop_methods_from_sidecar(contract)
        if extracted:
            print(
                f"[DEBUG] loop methods for {contract} taken from the analyzer sidecar"
            )
        else:
            try:
                ast_tree = parse_solidity(contract_code)
                extracted = extract_solidity_methods(ast_tree)
            except Exception as e:
                print(f"❌ Failed to parse {contract}: {e}")
                continue
        print(f"[DEBUG] extract_solidity_methods returned {len(extracted)} contract entries for {contract}")

        for contract_name, funcs in extracted.items():
            print(f"[DEBUG]  Contract {contract_name} has {len(funcs)} functions")
            for fname in funcs:
                theory_preds = []
                theory_obj = _get_theory_for_contract(theories, contract_name)
                if theory_obj is not None:
                    try:
                        theory_preds.extend(theory_obj.get_bools())
                    except Exception as e:
                        print(f"❌ Error extracting predicates for {contract_name}: {e}")
                methods.append((fname, contract_name, theory_preds))

    print(f"[DEBUG] get_methods_and_theories → total methods={len(methods)}, total theories={len(theories)}")
    return methods, theories



def _info_specs_for(contract_name, function_name):
    """
    Read the postconditions and invariants recorded for a method in its theory
    file.

    Without this the only postconditions available come from assert statements
    written into the contract by hand, so a contract that carries no asserts
    offers the mutation engine nothing to generalise, whatever the analysis
    inferred.
    """
    path = os.path.join(SOLIDITY_CONTRACTS_DIR, f"T{contract_name}.info")
    if not os.path.exists(path):
        return [], []

    posts, invs = [], []
    current = None
    section = None

    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return [], []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "== Method ==":
            section = "method"
            continue
        if line.startswith("== ") and line.endswith(" =="):
            section = {
                "== Postconditions ==": "post",
                "== Invariants ==": "inv",
            }.get(line)
            continue
        if section == "method":
            current = line
            section = None
        elif current == function_name and section == "post":
            posts.append(line)
        elif current == function_name and section == "inv":
            invs.append(line)

    return posts, invs


def process_with_commands(
    contract_names,
    theory_dir,
    method_only=None,
    printall=False,
    fullyqualified=False,
    expandquant=False,
    debug=False,
    timeout=60,
    only=0,
    serialize=False,
    skip=False,
    special=None,
    strict=True,
):
    """
    Top-level driver used by the CLI.
    """
    methods, theories = get_methods_and_theories(contract_names, theory_dir)

    if method_only:
        methods = [m for m in methods if m[0] == method_only]
        if not methods:
            print(f"[DEBUG] No methods match method_only={method_only} in contracts={contract_names}")
            return None

    print(f"[DEBUG] Found {len(methods)} methods for contracts {contract_names} using theory_dir={theory_dir}")
    for (fname, cname, preds) in methods:
        print(f"[DEBUG]  - method={fname}, contract={cname}, #theory_preds={len(preds)}")

    results = []

    for function_name, contract_name, function_theories in methods:
        contract_path = os.path.join(SOLIDITY_CONTRACTS_DIR, contract_name + EXTENSION)
        if not os.path.exists(contract_path):
            print(f"[WARN] Contract file missing for {contract_name} at {contract_path}")
            continue

        with open(contract_path, "r") as f:
            contract_code = f.read()

        try:
            ast_tree = parse_solidity(contract_code)
        except Exception as e:
            # The extractors below read the source directly, so the AST is only
            # used to confirm the function exists. Losing it is not a reason to
            # drop the method.
            print(f"[WARN] Could not parse {contract_name} for the AST gate: {e}")
            ast_tree = None

        # locate function node (not strictly needed for our extraction helpers, but kept)
        func_node = None
        for child in (ast_tree or {}).get("children", []):
            if child.get("type") == "ContractDefinition":
                for sub in child.get("nodes", []) or child.get("subNodes", []):
                    if (
                        sub.get("type") == "FunctionDefinition"
                        and sub.get("name") == function_name
                    ):
                        func_node = sub
                        break
            if func_node:
                break

        if not func_node and ast_tree is not None:
            print(f"[DEBUG] Skipping {function_name} in {contract_name}: function node not found in AST")
            continue

        # IMPORTANT: these extractors are what determine #pre/#post in your logs
        postconditions = extract_assert_statements(contract_code, function_name)
        preconditions = extract_require_statements(contract_code, function_name)

        info_posts, info_invs = _info_specs_for(contract_name, function_name)

        all_posts = postconditions + preconditions + info_posts
        posts_ast = _parse_posts_to_ast(all_posts)

        # Build a method-like object so SolidityMutator won't crash
        method_obj = _best_effort_seed_method(contract_code, function_name)

        print(
            f"[DEBUG] For {contract_name}.{function_name}: "
            f"#pre={len(preconditions)}, #post={len(postconditions)}, "
            f"#theory_preds={len(function_theories)}, #posts_ast={len(posts_ast)}"
        )

        # FIX #2: do NOT pass function_theories as invariants (expected invariants should be [])
        tracker = process_method(
            function_name,
            method_obj,
            posts_ast,
            all_posts,
            info_invs,
            theories,
            debug=debug,
            timeout=timeout,
            special=special,
            strict=strict,
        )

        results.append(tracker)

    return results if results else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate mutations for Solidity smart contracts."
    )
    parser.add_argument("-T", dest="theory_directory", default=".")
    parser.add_argument("-m", dest="method_name")
    parser.add_argument("--tofile", dest="ext")
    parser.add_argument("--command", dest="cmd")
    parser.add_argument("--fullnames", dest="fullyqualified", action="store_true")
    parser.add_argument(
        "-q",
        "--explicitquantifiers",
        dest="explicitquant",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="print_all",
        action="store_true",
    )
    parser.add_argument("--serialize", dest="serialize", action="store_true")
    parser.add_argument("--only", dest="only", type=int)
    parser.add_argument("--to", "--timeout", dest="timeout", type=int)
    parser.add_argument("--nonstrict", dest="strict", action="store_false")
    parser.add_argument("--debug", dest="debug_file")
    parser.add_argument("classes", nargs="+", metavar="C")

    args = parser.parse_args()
    debug = args.debug_file is not None
    if debug:
        logging.basicConfig(
            filename=args.debug_file,
            filemode="w",
            level=logging.DEBUG,
        )

    special_commands = None
    if args.cmd:
        special_commands = [[c.strip() for c in args.cmd.split(";")]]

    process_with_commands(
        contract_names=args.classes,
        theory_dir=args.theory_directory,
        method_only=args.method_name,
        printall=args.print_all,
        fullyqualified=args.fullyqualified,
        expandquant=args.explicitquant,
        debug=debug,
        timeout=args.timeout or 60,
        only=args.only or 0,
        serialize=args.serialize,
        strict=args.strict,
        special=special_commands,
    )
