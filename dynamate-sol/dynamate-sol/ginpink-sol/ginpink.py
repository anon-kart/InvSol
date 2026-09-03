import os
import re
from SolidityAST import make_binop, make_unop, make_implies  # Assuming utility functions for AST nodes
from SolidityInvariantParser import SolidityInvariantParser
import contextlib, io
from SolidityInvariantParser import parse_expr
from SolidityAST import convert_parser_expr  # ✅ Import it
from jmlvisitor import (
    IntSubstitutions,
    BooleanSubstitutions,
    PredicateExtractor,
    AgingSubstitutions,
    ResultRemover,
    OldAdder,
    WeakeningSubstitutions
)
# ---- debug switches (set to True only when you need spam) ----
DEBUG_READ = False       # for read_methods() / .info parsing
DEBUG_SUBS = False       # for substitute_all() / substitution passes
DEBUG_MUTATOR = False    # for SolidityMutator

# Directory where Solidity contract files are stored
SOLIDITY_CONTRACTS_DIR = ''
EXTENSION = ".info"

def qp(expr):
    # Silence parser spam unless a debug switch is on
    if DEBUG_READ or DEBUG_SUBS or DEBUG_MUTATOR:
        return parse_expr(expr)
    out_buf, err_buf = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
        return parse_expr(expr)

def read_contract(contract_name, location='.'):
    """
    Reads and parses a Solidity .info metadata file (theory-style), similar to GIN-DYN's read_class.
    Returns a SolPinkTheory object directly.
    """
    # ✅ FIX: always read .info, never use EXTENSION here
    filepath = os.path.join(location, contract_name + ".info")

    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    pkg = ""
    int_expressions = []
    bool_expressions = []

    in_pkg = False
    in_ints = False
    in_bools = False

    for line in lines:
        if not line or line.startswith("//"):
            continue

        # ✅ FIX: tolerate slight header variations
        if line.startswith("==") and "Package" in line:
            in_pkg = True
            in_ints = False
            in_bools = False
            continue

        if line.startswith("==") and "Integer" in line:
            in_pkg = False
            in_ints = True
            in_bools = False
            continue

        if line.startswith("==") and "Boolean" in line:
            in_pkg = False
            in_ints = False
            in_bools = True
            continue

        if in_pkg:
            pkg = line
        elif in_ints:
            int_expressions.append(line)
        elif in_bools:
            bool_expressions.append(line)

    return SolPinkTheory(contract_name, int_expressions, bool_expressions, pkg)

# 📌 Extract Solidity version and package information
def extract_package_info(contract_code):
    """
    Extracts package or module metadata (e.g., pragma version).
    """
    pragma_match = re.search(r'pragma solidity ([^;]+);', contract_code)
    return pragma_match.group(1) if pragma_match else "Unknown"

# 📌 Classify Solidity contract types
def classify_contract(node):
    """
    Classifies Solidity contracts as 'normal', 'library', or 'abstract'.
    """
    if node.get('kind') == 'library':
        return 'library'
    elif node.get('kind') == 'abstract':
        return 'abstract'
    return 'normal'

# 📌 Detect whether a function is static
def is_static_function(node):
    """
    Determines if a Solidity function is 'static' (i.e., does not modify state).
    """
    if 'stateMutability' in node:
        return node['stateMutability'] in ['pure', 'view']
    return False

def read_methods(contract_name, location='.'):
    """
    Parses a Solidity-style `.info` file (structured like GIN-DYN) and returns SolPinkMethod objects,
    along with their postconditions, invariants, and preconditions.

    :param contract_name: Name of the Solidity contract (without extension)
    :param location: Path to the directory containing the `.info` file
    :return: List of tuples (SolPinkMethod, postconditions, invariants, preconditions)
    """
    filepath = os.path.join(location, contract_name + EXTENSION)
    print(f"📄 Trying to read: {filepath}")
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    if DEBUG_READ:
        print("📄 Contents of the .info file:")
        for i, line in enumerate(lines, 1):
            print(f"  {i:02}: {repr(line)}")

    ms = []
    name = ''
    pkg = ''
    in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False

    ints = []
    bools = []
    refs = {}
    pres = []
    posts = []
    invs = []
    cmds = []
    in_templates = False
    template_bools = []

    # ------------------------------------------------------------
    # meta / synthetic lines that we want to IGNORE while reading
    META_EXACT = {
        "NoStateWrites();",
        "NoExternalCalls();",
        "HasExternalCalls();",
        "HasExternalCallsInLoop();",
        "NoExternalCallsInLoop();",
        ";",
    }
    META_PREFIXES = (
        "Emits(",
        "UpdatesArray(",
        "Accumulator(",
        "Guard(",
        "Update(",
        "HasExternalCalls(",
        "NoExternalCalls(",
        "NoStateWrites(",
        "NoExternalCallsInLoop(",
        "HasExternalCallsInLoop(",
    )
    # optional: drop boring ints early
    BORING_INTS = {"1", "-1", "2", "-2", "100"}
    # ------------------------------------------------------------

    for cl in lines:
        if DEBUG_READ:
            print("Parsed line →", repr(cl))
            print(f"    Flags: pre={in_pre}, post={in_post}, invs={in_invs}, cmd={in_cmd}")

        raw = cl.strip()

        # skip empties / comments early
        if raw == "" or raw.startswith("//"):
            continue

        # skip meta lines early (applies to all sections — post, invs, etc.)
        if raw in META_EXACT or any(raw.startswith(pref) for pref in META_PREFIXES):
            continue

        # --------------------------------------------------------
        # section markers
        # --------------------------------------------------------
        if cl == '== Package ==':
            in_pkg, in_method, in_static = True, False, False
            in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False

        elif cl.strip() == '== Method ==':
            if DEBUG_READ:
                print("📌 ENTERING Method Section")
            # flush previous method
            if name:
                if DEBUG_READ:
                    print(f"🧩 Appending method '{name}' with {len(posts)} postconditions")
                ms.append((name, static, ints, bools, refs, posts, invs, cmds, pres))

            # reset everything for new method
            name = ''
            static = False
            ints = []
            bools = []
            refs = {}
            pres = []
            posts = []
            invs = []
            cmds = []
            in_method = True
            in_pkg = in_static = in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False

        elif cl == '== Static ==':
            in_static = True
            in_pkg = in_method = in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False

        elif cl == '== Integer expressions ==':
            in_ints = True
            in_pkg = in_method = in_static = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False

        elif cl == '== Boolean expressions ==':
            in_bools = True
            in_pkg = in_method = in_static = in_ints = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False

        elif cl == '== Ref expressions ==':
            in_refs = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False

        elif cl.strip() == '== Preconditions ==':
            if DEBUG_READ:
                print("📌 ENTERING Precondition Section")
            in_pre = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_post = in_invs = in_cmd = False
            in_templates = False

        elif cl.strip() == '== Postconditions ==':
            if DEBUG_READ:
                print("📌 ENTERING Postcondition Section")
            in_post = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_pre = in_invs = in_cmd = False
            in_templates = False

        elif cl.strip() == '== Invariants ==':
            if DEBUG_READ:
                print("📌 ENTERING Invariant Section")
            in_invs = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_post = in_pre = in_cmd = False
            in_templates = False

        elif cl.strip() == '== Commands ==':
            if DEBUG_READ:
                print("📌 ENTERING Commands Section")
            in_cmd = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_post = in_pre = in_invs = False
            in_templates = False

        elif cl == '== Template boolean expressions ==':
            in_templates = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False

        # --------------------------------------------------------
        # content of sections
        # --------------------------------------------------------
        elif in_templates:
            template_bools.append(cl)

        elif in_pkg:
            pkg = cl

        elif in_method:
            # first non-header line after "== Method =="
            name = cl
            in_method = False

        elif in_static:
            static = (cl == 'Y')

        elif in_ints:
            # optional: skip very boring ints
            if cl not in BORING_INTS:
                ints.append(cl)

        elif in_bools:
            # only keep boolean templates that mention at least one identifier
            # (so constant-only stuff like "1 <= -1" gets dropped)
            if re.search(r'\b[A-Za-z_][A-Za-z0-9_]*\b', cl):
                bools.append(cl)

        elif in_refs:
            if ':' in cl:
                key, ids = cl.split(':', 1)
                refs[key.strip()] = [i.strip() for i in ids.split(',')]

        elif in_pre:
            pres.append(cl)

        elif in_post:
            if DEBUG_READ:
                print(f"➕ Adding postcondition line: {repr(cl)}")
            posts.append(cl)

        elif in_invs:
            invs.append(cl)

        elif in_cmd:
            cmds.append([x.strip() for x in cl.split(';')])

    # append final method
    if name:
        if DEBUG_READ:
            print(f"🧩 Final append of method '{name}' with {len(posts)} posts")
        ms.append((name, static, ints, bools, refs, posts, invs, cmds, pres))

    # =====================================================================
    # build final result
    # =====================================================================
    result = []
    for m in ms:
        classlist = []
        for c in list(m[4].keys()) + [contract_name]:
            classlist.append(read_contract(c, location))

        method_obj = SolPinkMethod(
            method_name=m[0],
            contract_name=contract_name,
            intlist=m[2],
            boollist=m[3],
            refdict=m[4],
            classlist=classlist,
            is_static=m[1],
            commands=m[7],
            pkg=pkg
        )

        # ---------- parse pres ----------
        parsed_pres = []
        for p in m[8]:
            try:
                e = qp(p.strip().rstrip(';'))
                if e:
                    parsed_pres.append(e)
            except Exception as ex:
                print(f"[ERROR] Failed to parse precondition: {p} → {ex}")

        # ---------- parse posts (with 2nd-level filter) ----------
        parsed_posts = []
        if DEBUG_READ:
            print(f"🧾 Raw m[5] (postconditions list): {m[5]}")

        # second-level meta filters (no trailing ';' here)
        META_EXACT_2 = {
            "NoStateWrites()",
            "NoExternalCalls()",
            "HasExternalCalls()",
            "HasExternalCallsInLoop()",
            "NoExternalCallsInLoop()",
            "",
        }
        META_PREFIXES_2 = (
            "Emits(",
            "UpdatesArray(",
            "Accumulator(",
            "Guard(",
            "Update(",
            "HasExternalCalls(",
            "NoExternalCalls(",
            "NoStateWrites(",
            "NoExternalCallsInLoop(",
            "HasExternalCallsInLoop(",
        )

        for p in m[5]:
            cleaned = p.strip().rstrip(';')
            if DEBUG_READ:
                print(f"🧪 Trying to parse postcondition: '{cleaned}'")

            # skip meta / synthetic one more time
            if cleaned in META_EXACT_2 or any(cleaned.startswith(pref) for pref in META_PREFIXES_2):
                if DEBUG_READ:
                    print(f"⚙️ Skipping synthetic/meta postcondition: {cleaned}")
                continue

            try:
                e = qp(cleaned)
                if e:
                    e.cur_pos = True
                    if DEBUG_READ:
                        print(f"🔬 Raw expr: {p.strip()} → Parsed: {e.text()}")
                        print(f"🔍 Result: {e} (type={type(e)})")
                    parsed_posts.append(e)
                    if DEBUG_READ:
                        print(f"✅ Appended postcondition: {e.text()}")
                        print(f"📊 Total postconditions so far: {len(parsed_posts)}")
                        for idx, post in enumerate(parsed_posts, 1):
                            print(f"   🔹 [{idx}] {post.text()}")
                else:
                    if DEBUG_READ:
                        print(f"⚠️ parse_expr returned None for: '{cleaned}'")
            except Exception as ex:
                print(f"❌ Exception while parsing postcondition: '{cleaned}' → {ex}")

        # ---------- parse invariants ----------
        parsed_invs = []
        for p in m[6]:
            cleaned = p.strip().rstrip(';')
            if not cleaned or cleaned == ";":
                continue
            # also ignore meta-like invariant lines
            if cleaned in META_EXACT or any(cleaned.startswith(pref) for pref in META_PREFIXES):
                continue
            try:
                e = qp(cleaned)
                if e:
                    parsed_invs.append(e)
            except Exception as ex:
                print(f"[ERROR] Failed to parse invariant: {p} → {ex}")

        result.append((method_obj, parsed_posts, parsed_invs, parsed_pres))
        if DEBUG_READ:
            print(f"📋 Final method: {method_obj.name}, posts: {len(parsed_posts)}, invs: {len(parsed_invs)}, pres: {len(parsed_pres)}")

    return result


# 📌 Extract integer expressions
def extract_integer_expressions(contract_code, function_name):
    """
    Extracts integer expressions from a Solidity function.
    """
    integer_expressions = []
    function_pattern = rf'function {function_name}\s*\(.*?\)\s*.*?{{(.*?)}}'
    function_match = re.search(function_pattern, contract_code, re.DOTALL)

    if function_match:
        function_body = function_match.group(1)
        integer_expressions = re.findall(r'(\w+\s*[+\-*/]\s*\w+)', function_body)

    return integer_expressions

# 📌 Extract boolean expressions and their negations
def extract_boolean_expressions(contract_code, function_name):
    """
    Extracts boolean conditions from Solidity functions and generates negated variants.
    """
    boolean_expressions = []
    function_pattern = rf'function {function_name}\s*\(.*?\)\s*.*?{{(.*?)}}'
    function_match = re.search(function_pattern, contract_code, re.DOTALL)

    if function_match:
        function_body = function_match.group(1)
        boolean_expressions = re.findall(r'while\s*\((.*?)\)|for\s*\(.*?;(.*?);.*?\)', function_body)

    # Generate negations
    negated_expressions = [f"!({expr})" for expr in boolean_expressions]
    
    return boolean_expressions + negated_expressions

# 📌 Extract reference variables
def extract_references(contract_code, function_name):
    """
    Extracts referenced storage variables from a Solidity function.
    """
    references = []
    function_pattern = rf'function {function_name}\s*\(.*?\)\s*.*?{{(.*?)}}'
    function_match = re.search(function_pattern, contract_code, re.DOTALL)

    if function_match:
        function_body = function_match.group(1)
        references = re.findall(r'storage\s+(\w+)|mapping\s*\(.*?\)\s+(\w+)', function_body)

    return references

# 📌 Extract `require` conditions (preconditions)
def extract_require_statements(contract_code, function_name):
    """
    Extracts `require` statements from a Solidity function to determine preconditions.
    """
    require_statements = []
    function_pattern = rf'function {function_name}\s*\(.*?\)\s*.*?{{(.*?)}}'
    function_match = re.search(function_pattern, contract_code, re.DOTALL)

    if function_match:
        function_body = function_match.group(1)
        require_statements = re.findall(r'require\s*\((.*?)\);', function_body)

    return require_statements

# 📌 Extract `assert` conditions (postconditions)
def extract_assert_statements(contract_code, function_name):
    """
    Extracts `assert` statements from a Solidity function to determine postconditions.
    """
    assert_statements = []
    function_pattern = rf'function {function_name}\s*\(.*?\)\s*.*?{{(.*?)}}'
    function_match = re.search(function_pattern, contract_code, re.DOTALL)

    if function_match:
        function_body = function_match.group(1)
        assert_statements = re.findall(r'assert\s*\((.*?)\);', function_body)

    return assert_statements


# 📌 Extract commands (Solidity operations)
def extract_function_commands(contract_code, function_name):
    """
    Extracts key operations (commands) inside a Solidity function.
    """
    commands = []
    function_pattern = rf'function {function_name}\s*\(.*?\)\s*.*?{{(.*?)}}'
    function_match = re.search(function_pattern, contract_code, re.DOTALL)

    if function_match:
        function_body = function_match.group(1)
        commands = re.findall(r'(msg\.sender|msg\.value|selfdestruct|emit|transfer|require|assert)', function_body)

    return commands

def substitute(root, exps, n, subn):
    """
    Perform exactly `n` substitutions of expressions `exps` into `root`,
    using substitution logic class/function `subn` (like 'IntSubstitutions').
    """
    if n <= 0:
        return [root]

    results = []
    for e in exps:
        # Recurse to apply (n-1) substitutions on the tree
        for r in substitute(root, exps, n - 1, subn):
            try:
                # Apply the substitution logic (e into r)
                subs = eval(subn)(e, r)
                results.extend(subs)
            except Exception as ex:
                etext = e.text() if hasattr(e, "text") else str(e)
                rtext = r.text() if hasattr(r, "text") else str(r)
                print(f"❌ Substitution error: {etext}, {rtext} → {ex}")
    return list(set(results))  # Remove duplicates

def substitute_all(root_expr_or_node, exprs, n, sub_class_name):
    """
    Tries all substitution depths from 0 up to n using the specified substitution class.
    Accepts either a string (expr) or an already parsed AST.
    """
    # ---- 1) parse root if it's a string ----
    if isinstance(root_expr_or_node, str):
        root = qp(root_expr_or_node)
        if not root:
            if DEBUG_SUBS:
                print(f"❌ Failed to parse root expression: '{root_expr_or_node}'")
            return []
    else:
        root = root_expr_or_node

    # enable substitution tracking (your code was doing this)
    root.cur_pos = True

    # ---- 2) clean expr list (drop None) ----
    clean_exprs = [e for e in exprs if e is not None]

    if DEBUG_SUBS:
        print(f"🔍 Substituting in: '{root.text()}'")
        # don't spam: show at most 15 exprs
        preview = [e.text() for e in clean_exprs[:15]]
        more = len(clean_exprs) - len(preview)
        if more > 0:
            preview.append(f"... (+{more} more)")
        print(f"🧩 Using {len(clean_exprs)} expressions: {preview}")

    result = []

    # ---- 3) try all depths ----
    for d in range(n + 1):
        if DEBUG_SUBS:
            print(f"🔁 Substitution pass with depth {d}")
        try:
            partial = substitute(root, clean_exprs, d, sub_class_name)
            if DEBUG_SUBS:
                print(f"✅ Depth {d} → {len(partial)} substitutions")
            result.extend(partial)
        except Exception as ex:
            # even with DEBUG_SUBS = False, errors should be visible
            print(f"❌ Error during substitution at depth {d}: {ex}")

    # ---- 4) dedupe by object identity / text ----
    # (simple way: just use set(result) like you had)
    return list(set(result))

class SolPinkType(object):
    """
    Solidity equivalent of DynaMate's `PinkType`.
    Stores and retrieves integer and boolean expressions grouped by argument count.
    """

    def __init__(self, contract_name, intlist, boollist, pkg=""):
        """
        Initializes a Solidity contract representation with extracted expressions.

        :param contract_name: Name of the Solidity contract
        :param intlist: List of integer expressions extracted
        :param boollist: List of boolean expressions extracted
        :param pkg: Package/module information (pragma solidity version)
        """
        self.name = contract_name
        self.package = pkg
        self.ints = self._group_expressions(intlist)
        self.bools = self._group_expressions(boollist)

    def _group_expressions(self, expr_list):
        """
        Groups expressions based on the number of arguments (placeholders '#').

        :param expr_list: List of expressions (strings)
        :return: Dictionary grouping expressions by argument count
        """
        grouped = {}
        for expr in expr_list:
            arg_count = expr.count("#")
            if arg_count not in grouped:
                grouped[arg_count] = []
            grouped[arg_count].append(expr)
        return grouped

    def get_ints(self, obj: str = "", n: int = 0, base=None):
        """
        Instantiate integer templates with:
          - `obj` as receiver (if needed),
          - `base` integer expressions for `#` placeholders,
          - up to `n` arguments / substitution depth.

        Returns a **deduplicated list of AST nodes**.
        """
        if base is None:
            base = []

        results = []

        for m in range(n + 1):
            if m not in self.ints:
                continue

            for expr in self.ints[m]:
                expr = expr.strip()
                if not expr or expr.endswith("."):
                    # 🚫 Skip malformed base expressions like "foo."
                    continue

                # Attach object or replace "$"
                if "$" in expr and obj:
                    updated_expr = expr.replace("$", obj)
                elif "$" in expr and not obj:
                    # If there is a "$" but no obj, leave as is
                    updated_expr = expr
                elif obj and not any(sym in expr for sym in [".", "(", "["]):
                    # Simple identifier: prefix as obj.expr
                    updated_expr = f"{obj}.{expr}"
                else:
                    updated_expr = expr

                # Instantiate templates using base expressions
                substituted = substitute_all(updated_expr, base, m, "substitute_expressions")

                for s in substituted:
                    try:
                        # If it's already an AST node, don't re-parse
                        if hasattr(s, "text"):
                            parsed = s
                        else:
                            parsed = qp(s)

                        if parsed:
                            text = parsed.text().strip()
                            if not text.endswith("."):
                                results.append(parsed)
                            else:
                                # malformed like "foo." again
                                print(f"🚫 Skipping invalid substituted expr: '{text}'")
                    except Exception as ex:
                        s_repr = s.text() if hasattr(s, "text") else repr(s)
                        print(f"❌ parse_expr failed for: {s_repr} → {ex}")

        # 🔁 Deduplicate by textual representation
        seen = set()
        unique = []
        for e in results:
            if not e:
                continue
            t = e.text() if hasattr(e, "text") else str(e)
            if t not in seen:
                seen.add(t)
                unique.append(e)

        return unique

    def get_bools(self, obj: str = "", n: int = 2, base=None, refs=None, fixedArgs=None):
        """
        Retrieves boolean expressions, supporting argument substitution.

        - `obj`      : receiver (e.g., "this" or a variable name)
        - `refs`     : list of reference variables the templates are instantiated over
        - `fixedArgs`: fixed arguments for '#' placeholders
        - `base`     : integer expressions used for remaining '#' placeholders

        Returns **deduplicated AST nodes** instead of plain strings.
        """
        if base is None:
            base = []
        if refs is None:
            refs = []
        if fixedArgs is None:
            fixedArgs = []

        results = []

        # Determine targets for `$`:
        #  - if refs exist, we instantiate over those
        #  - otherwise, if obj is present, use that as the receiver
        #  - fallback: a single "" (no replacement)
        targets = refs if refs else ([obj] if obj else [""])

        for m in range(n + 1):
            if m not in self.bools:
                continue

            for expr in self.bools[m]:
                expr = expr.strip()
                if not expr:
                    continue

                for ref in targets:
                    # Replace '$' with current target if non-empty
                    if ref:
                        new_expr = expr.replace("$", ref)
                    else:
                        new_expr = expr

                    # Replace each '#' with fixed arguments first
                    tmp = new_expr
                    for arg in fixedArgs:
                        tmp = tmp.replace("#", arg, 1)

                    # Remaining '#': substitute using base expressions
                    remaining_subs = max(0, m - len(fixedArgs))
                    substituted_exprs = substitute_all(tmp, base, remaining_subs, "substitute_expressions")

                    # --- Fallback: if we have '#' placeholders but no base ints yet,
                    # instantiate remaining '#' with 0 so we still return something ---
                    if (not substituted_exprs) and ("#" in tmp):
                        tmp0 = tmp
                        while "#" in tmp0:
                            tmp0 = tmp0.replace("#", "0", 1)
                        substituted_exprs = [tmp0]

                    # ✅ Parse to ASTs
                    for s in substituted_exprs:
                        # If s is a string, we can safely check for "ZZZZ"
                        if isinstance(s, str) and "ZZZZ" in s:
                            # Filter out clearly broken substitutions
                            continue

                        try:
                            # Reuse ASTs directly; only parse strings
                            if hasattr(s, "text"):
                                parsed = s
                            else:
                                parsed = qp(s)

                            if parsed:
                                results.append(parsed)
                        except Exception as ex:
                            s_repr = s.text() if hasattr(s, "text") else repr(s)
                            print(f"❌ parse_expr failed in get_bools for '{s_repr}' → {ex}")

        # 🔁 Deduplicate by textual representation
        seen = set()
        unique = []
        for e in results:
            if not e:
                continue
            t = e.text() if hasattr(e, "text") else str(e)
            if t not in seen:
                seen.add(t)
                unique.append(e)

        return unique


class SolPinkTheory(SolPinkType):
    """
    Solidity equivalent of DynaMate's `PinkTheory`.
    Represents contract-level static analysis.
    """

    def __init__(self, contract_name, intlist, boollist, pkg=""):
        """
        Initializes a Solidity contract as a static theory object.
        
        :param contract_name: Solidity contract name
        :param intlist: List of integer expressions
        :param boollist: List of boolean expressions
        :param pkg: Package/module info (pragma Solidity version)
        """
        super().__init__(contract_name, intlist, boollist, pkg)
        self.static = True  # Mark as a static analysis object

class SolPinkMethod:
    """
    AST-based version of Solidity's method analyzer, modeled after DynaMate's PinkMethod.
    Handles method-local expressions, references, and contract-level context.
    """

    def __init__(self, method_name, contract_name, intlist, boollist, refdict, classlist, is_static=False, commands=None, pkg=""):
        self.name = method_name
        self.contract = contract_name
        self.package = pkg
        self.is_static = is_static
        self.refs = refdict or {}
        self.commands = commands if commands else []
        self.arity = 0  # Number of arguments in method

        # Class-level context mapping: contract name → SolPinkType
        self.classes = {c.name: c for c in classlist}
        self.enclosing = self.classes.get(contract_name)

        # Local expressions parsed into AST
        self.ints = [
            parsed for e in intlist
            if not re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*', e)  # Skip pure identifiers
            for parsed in [qp(e)] if parsed
        ]
        self.bools = [qp(e) for e in boollist if qp(e)]

        # If non-static, include contract-level expressions from `this`
        if not is_static and self.enclosing:
            self.ints += self.enclosing.get_ints(obj='', n=0, base=self.ints)

    def get_ints(self):
        """
        Retrieves all integer expressions visible in this method (local + from references).
        Returns AST nodes only.
        """
        expressions = list(self.ints)

        for contract_name, ref_list in self.refs.items():
            contract_type = self.classes.get(contract_name)

            # Skip if class is None or likely a primitive
            if not contract_type:
                continue

            # Optional extra: sanity check for int/bool-only contracts
            if not contract_type.ints and not contract_type.bools:
                continue

            for ref in ref_list:
                # Only apply if contract_type has real expressions to contribute
                expressions += contract_type.get_ints(obj=ref, n=self.arity, base=self.ints)

        cleaned = []
        for e in expressions:
            if e and hasattr(e, "text"):
                t = e.text().strip()
                if t and not t.endswith('.') and not t.endswith('.;'):
                    cleaned.append(e)
                else:
                    print(f"🚫 [Filtered bad method int] {t}")
        return self._deduplicate_asts(cleaned)


    def get_bools(self):
        """
        Retrieves all boolean expressions visible in this method (local + from references).
        Returns AST nodes only.
        """
        expressions = list(self.bools)
        for contract_name, ref_list in self.refs.items():
            contract_type = self.classes.get(contract_name)
            if contract_type:
                for ref in ref_list:
                    expressions += contract_type.get_bools(obj=ref, n=self.arity, base=self.ints)
        return self._deduplicate_asts(expressions)

    def get_refs(self):
        """
        Returns all reference variables in this method.
        """
        return [ref for _, refs in self.refs.items() for ref in refs]

    def set_arity(self, n):
        """
        Sets arity (number of arguments) for parametric expression instantiations.
        """
        if n >= 0:
            self.arity = n

    def _deduplicate_asts(self, asts):
        """
        Deduplicates a list of AST nodes by comparing their `.text()` representations.
        """
        seen = set()
        unique = []
        for ast in asts:
            if not ast:
                continue
            text_repr = ast.text()
            if text_repr not in seen:
                seen.add(text_repr)
                unique.append(ast)
        return unique

class SolidityMutator:
    """
    Solidity equivalent of DynaMate's `CommonMutator`.
    Applies integer and boolean mutations for loop invariant inference.
    """

    # ------------------------------------------------------------------
    # Helper: decide if an integer expression should be treated as
    # a scalar (i.e., safe to use in <, <=, ==, +, - templates).
    # We explicitly *exclude* reference variables like `grid`,
    # `row`, `deposits`, `depositorKeys`, etc. so we never build
    # junk like (c + grid) or (index + deposits).
    # ------------------------------------------------------------------
    def _is_scalar_int_expr(self, e):
        """
        Decide if an integer expression is a *scalar*:
        - reject anything that obviously involves reference-like names
        (arrays, mappings, storage objects like `grid`, `row`, etc.)
        - reject malformed stuff
        - optionally avoid overly complex expressions
        """
        import re
        if e is None or not hasattr(e, "text"):
            return False

        t = e.text().strip()
        if not t:
            return False

        # filter out clearly broken stuff
        if "ZZZZ" in t:
            return False
        if t.endswith(".") or t.endswith(".;"):
            return False

        # names that we consider non-scalar (arrays/mappings/refs)
        ref_names = getattr(self, "_ref_names", set())

        # reject any expression that mentions those names
        for r in ref_names:
            if not r:
                continue
            if re.search(rf"\b{re.escape(r)}\b", t):
                return False

        # extract identifiers
        ids = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", t)

        # ⭐ NEW RULE: reject pure constant expressions
        # (no identifiers → meaningless scalar seed)
        if not ids:
            return False

        # avoid multi-var complex algebraic junk
        if len(set(ids)) > 3:
            return False

        return True


    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, method, theories, posts):
        import re
        self.method = method
        self.theories = {t.name: t for t in theories}

        # ✅ Use already parsed ASTs (no re-parsing)
        self.posts = [p for p in posts if p is not None]

        # normalise method-call style posts
        for post in self.posts:
            if hasattr(post, "args") and isinstance(post.args, list):
                post.args = [convert_parser_expr(arg) for arg in post.args]

        # ---------------------------------------------------------
        # Infer non-scalar / reference-like names
        # ---------------------------------------------------------
        self._ref_names = set(self.method.get_refs()) if hasattr(self.method, "get_refs") else set()

        # also infer from boolean guards (e.g., grid.length, arr[i])
        try:
            for b in self.method.get_bools():
                if not hasattr(b, "text"):
                    continue
                bt = b.text()
                for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.", bt):
                    self._ref_names.add(m.group(1))
                for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\[", bt):
                    self._ref_names.add(m.group(1))
        except Exception as ex:
            if DEBUG_MUTATOR:
                print(f"⚠️ Failed inferring ref-like names: {ex}")

        # 🔍 start from method.get_ints(), but immediately filter to scalar-only
        raw_ints = self.method.get_ints()
        self.method_ints = [e for e in raw_ints if self._is_scalar_int_expr(e)]

        self.active_preds = []
        self.weakening_preds = []
        self.instantiated = False

        if DEBUG_MUTATOR:
            print("🧪 SolidityMutator initialised")
            print("   • posts:", [p.text() for p in self.posts])
            print("   • method ints:", [i.text() for i in self.method_ints])
            print("   • ref names:", self._ref_names)

    # ------------------------------------------------------------------
    # ❶ Variable-substitution family  (wrapper around `mutations`)
    # ------------------------------------------------------------------
    def mutations(self, n=1):
        if DEBUG_MUTATOR:
            print("🧪 Running `mutations()`")
            print(f"🔍 Posts: {[p.text() for p in self.posts]}")
            print(f"🔍 Method ints: {[i.text() for i in self.method_ints]}")

        res = []
        for p in self.posts:
            m = substitute_all(p, self.method_ints, n, "IntSubstitutions")
            if DEBUG_MUTATOR:
                print(f"🔁 Substituting on: {p.text()} → {len(m)} mutations")
            res += m
        return res

    def variable_substitution_mutations(self, n=1):
        """
        Family 1: variable / scalar substitutions, as in the paper.
        This is essentially what `mutations()` already does.
        """
        return self.mutations(n)

    # ------------------------------------------------------------------
    # ❷ Boundary-adjustment family (aging + small literal shifts)
    # ------------------------------------------------------------------
    def mutations_and_aging(self, n=1, n_age=1):
        bm = self.mutations(n)
        aging_plus = qp("+1")
        aging_minus = qp("-1")
        res = []
        for m in bm:
            res += substitute_all(m, [aging_plus, aging_minus], n_age, "AgingSubstitutions")
        return bm + res

    def boundary_adjustment_mutations(self, literals=(0, 1), deltas=(-1, 1)):
        """
        Family 2: adjust numeric boundaries on simple comparisons,
        e.g.  0 <= i   →   1 <= i,  -1 <= i
        Only touches *numeric literals* to keep things sane.
        """
        import re
        results = []
        seen = set()

        # collect all boolean-like predicates to tweak
        candidates = []
        candidates.extend(self.posts or [])
        candidates.extend(self.method.get_bools() or [])
        candidates.extend(self.weakening_preds or [])
        candidates.extend(self.active_preds or [])

        for p in candidates:
            if p is None or not hasattr(p, "text"):
                continue
            txt = p.text()
            # crude parse for single comparison: LHS op RHS
            m = re.match(r"\s*(.+?)\s*(<=|<|>=|>|==|!=)\s*(.+?)\s*$", txt)
            if not m:
                continue
            lhs, op, rhs = m.group(1).strip(), m.group(2), m.group(3).strip()

            def is_int_literal(s):
                try:
                    int(s)
                    return True
                except Exception:
                    return False

            # left literal
            if is_int_literal(lhs):
                base = int(lhs)
                if base in literals:
                    for d in deltas:
                        new_lhs = str(base + d)
                        new_txt = f"{new_lhs} {op} {rhs}"
                        if new_txt == txt:
                            continue
                        try:
                            q = qp(new_txt)
                            t = q.text()
                            if t not in seen:
                                seen.add(t)
                                results.append(q)
                        except Exception:
                            continue

            # right literal
            if is_int_literal(rhs):
                base = int(rhs)
                if base in literals:
                    for d in deltas:
                        new_rhs = str(base + d)
                        new_txt = f"{lhs} {op} {new_rhs}"
                        if new_txt == txt:
                            continue
                        try:
                            q = qp(new_txt)
                            t = q.text()
                            if t not in seen:
                                seen.add(t)
                                results.append(q)
                        except Exception:
                            continue

        if DEBUG_MUTATOR:
            print(f"✅ Boundary-adjustment family produced {len(results)} mutations")
        return results

    # ------------------------------------------------------------------
    # ❸ Constraint-relaxation family: tweak comparison operators.
    # ------------------------------------------------------------------
    def constraint_relaxation_mutations(self):
        """
        Family 3: constraint relaxation / strengthening on a single
        comparison:
            <  ↔ <=,  > ↔ >=,  == ↔ <= / >=
        """
        import re

        relax_map = {
            "<": ["<=", "=="],
            "<=": ["<", "=="],
            ">": [">=", "=="],
            ">=": [">", "=="],
            "==": ["<=", ">="],
            "!=": []  # usually skip != for now
        }

        results = []
        seen = set()

        candidates = []
        candidates.extend(self.posts or [])
        candidates.extend(self.method.get_bools() or [])
        candidates.extend(self.weakening_preds or [])
        candidates.extend(self.active_preds or [])

        for p in candidates:
            if p is None or not hasattr(p, "text"):
                continue
            txt = p.text().strip()
            if not txt:
                continue

            # ensure exactly one comparison operator to avoid mangling
            ops_pat = r"(<=|>=|==|!=|<|>)"
            ops_found = re.findall(ops_pat, txt)
            if len(ops_found) != 1:
                continue
            op = ops_found[0]
            if op not in relax_map:
                continue

            parts = re.split(ops_pat, txt, maxsplit=1)
            if len(parts) != 3:
                continue
            lhs, _old, rhs = parts[0].strip(), parts[1], parts[2].strip()

            for new_op in relax_map[op]:
                new_txt = f"{lhs} {new_op} {rhs}"
                if new_txt == txt:
                    continue
                try:
                    q = qp(new_txt)
                    t = q.text()
                    if t not in seen:
                        seen.add(t)
                        results.append(q)
                except Exception:
                    continue

        if DEBUG_MUTATOR:
            print(f"✅ Constraint-relaxation family produced {len(results)} mutations")
        return results

    # ------------------------------------------------------------------
    # ❹ Quantifier-instantiation family.
    # ------------------------------------------------------------------
    def _guess_loop_indices(self):
        """
        Heuristic: pick scalar names like i, j, k, index, r, c, row, col.

        method_ints comes from extract_integer_expressions, whose pattern only
        matches binary arithmetic such as "i + 1", so it never yields a bare
        index name on its own. The predicates the mutator is about to work on
        do mention the index, so they are scanned as well.
        """
        import re

        candidates = {"i", "j", "k", "index", "idx", "r", "c", "row", "col"}
        names = []

        def note(token):
            if token in candidates and token not in names:
                names.append(token)

        for e in self.method_ints:
            if not hasattr(e, "text"):
                continue
            note(e.text().strip())

        if names:
            return names

        texts = []
        for source in (self.posts or [], getattr(self, "method_bools", []) or []):
            for e in source:
                if hasattr(e, "text"):
                    try:
                        texts.append(e.text())
                    except Exception:
                        continue
        for text in texts:
            for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
                note(token)

        return names

    def quantifier_instantiation_mutations(self):
        """
        Family 4: instantiate simple quantified predicates like

            forall i; 0 <= i < n ==> P(i)

        into concrete ones:

            P(i),  P(j),  P(index), ...

        based on available loop indices.
        """
        import re

        indices = self._guess_loop_indices()
        if not indices:
            return []

        results = []
        seen = set()

        candidates = self.posts or []
        for p in candidates:
            if p is None or not hasattr(p, "text"):
                continue
            txt = p.text()
            if "forall" not in txt and "\\forall" not in txt and "exists" not in txt:
                continue

            # try to extract bound variable name
            m = re.search(r"(?:forall|\\forall|exists)\s+([A-Za-z_][A-Za-z0-9_]*)", txt)
            if not m:
                continue
            bound = m.group(1)

            # take body after ==> as the property to instantiate
            if "==>" not in txt:
                continue
            body_str = txt.split("==>", 1)[1].strip().rstrip(";")

            for idx in indices:
                # The quantifier's own variable is not a loop index. Leaving it
                # in would emit the body unchanged, with a free variable, as
                # though it were an invariant.
                if idx == bound:
                    continue
                inst_body = body_str.replace(bound, idx)
                try:
                    q = qp(inst_body)
                    t = q.text()
                    if t not in seen:
                        seen.add(t)
                        results.append(q)
                except Exception:
                    continue

        if DEBUG_MUTATOR:
            print(f"✅ Quantifier-instantiation family produced {len(results)} mutations")
        return results

    # ------------------------------------------------------------------
    # ❺ Conditional-splitting family.
    # ------------------------------------------------------------------
    def conditional_splitting_mutations(self):
        """
        Family 5: split conjunctions A && B into implications
            A ==> B   and   B ==> A
        This mirrors the 'conditional splitting' flavour in the paper.
        """
        results = []
        seen = set()

        candidates = self.posts or []
        for p in candidates:
            if p is None or not hasattr(p, "text"):
                continue
            txt = p.text()
            if "&&" not in txt or "||" in txt:
                continue
            parts = [s.strip() for s in txt.split("&&")]
            if len(parts) != 2:
                continue
            left_txt, right_txt = parts
            try:
                left_q = qp(left_txt)
                right_q = qp(right_txt)
                imp1 = make_implies(left_q, right_q)
                imp2 = make_implies(right_q, left_q)
                for q in (imp1, imp2):
                    if q is None:
                        continue
                    t = q.text()
                    if t not in seen:
                        seen.add(t)
                        results.append(q)
            except Exception:
                continue

        if DEBUG_MUTATOR:
            print(f"✅ Conditional-splitting family produced {len(results)} mutations")
        return results

    # ------------------------------------------------------------------
    # Boolean & predicate-based mutations (existing families)
    # ------------------------------------------------------------------
    def boolean_mutations(self, n=1):
        unneg = []
        if not self.instantiated:
            for p in self.active_preds:
                if p is None:
                    continue
                try:
                    unneg += substitute_all(p, self.method_ints, n, "IntSubstitutions")
                except Exception as ex:
                    print(f"⚠️ Error during boolean IntSubstitutions: {ex}")
        else:
            unneg = [p for p in self.active_preds if p is not None]

        # dedup unneg
        seen_unneg = set()
        cleaned_unneg = []
        for u in unneg:
            if u is None:
                continue
            t = u.text() if hasattr(u, "text") else str(u)
            if t not in seen_unneg:
                seen_unneg.add(t)
                cleaned_unneg.append(u)
        unneg = cleaned_unneg

        # negations
        neg = []
        seen_neg = set()
        for m in unneg:
            try:
                nm = make_unop("!", m)
                t = nm.text() if hasattr(nm, "text") else str(nm)
                if t not in seen_neg:
                    seen_neg.add(t)
                    neg.append(nm)
            except Exception as ex:
                print(f"⚠️ Failed to negate predicate: {ex}")

        muts = unneg + neg

        res = []
        for p in self.posts:
            if p is None:
                continue
            try:
                res += substitute_all(p, muts, n, "BooleanSubstitutions")
            except Exception as ex:
                print(f"⚠️ BooleanSubstitutions failed: {ex}")

        # final dedup
        seen = set()
        uniq = []
        for r in res:
            if r is None:
                continue
            t = r.text() if hasattr(r, "text") else str(r)
            if t not in seen:
                seen.add(t)
                uniq.append(r)

        return uniq

    # ------------------------------------------------------------------
    def predicate_mutations(self, n=1, more=0, variants=True):
        unneg = []
        try:
            if not self.instantiated:
                for p in self.active_preds:
                    if p is None:
                        continue
                    unneg += substitute_all(p, self.method_ints, n, "IntSubstitutions")
            else:
                for p in self.active_preds:
                    if p is None:
                        continue
                    unneg += substitute_all(p, self.method_ints, more, "IntSubstitutions")
        except Exception as e:
            print(f"⚠️ Error during predicate substitution: {e}")

        # dedup
        seen_unneg = set()
        cleaned_unneg = []
        for u in unneg:
            if u is None:
                continue
            t = u.text() if hasattr(u, "text") else str(u)
            if t not in seen_unneg:
                seen_unneg.add(t)
                cleaned_unneg.append(u)
        unneg = cleaned_unneg

        if not variants:
            return unneg

        # negations
        neg = []
        seen_neg = set()
        for m in unneg:
            try:
                nm = make_unop("!", m)
                t = nm.text() if hasattr(nm, "text") else str(nm)
                if t not in seen_neg:
                    seen_neg.add(t)
                    neg.append(nm)
            except Exception as ex:
                print(f"⚠️ Failed to negate predicate: {ex}")

        muts = unneg + neg

        bools = [b for b in (self.weakening_preds + self.method.get_bools()) if b is not None]

        res = []
        import re
        for m in muts:
            if m is None:
                continue
            m_txt = m.text() if hasattr(m, "text") else str(m)

            for b in bools:
                if b is None:
                    continue

                b_txt = b.text() if hasattr(b, "text") else str(b)

                # ❌ skip boolean seeds which contain *no identifiers*
                if not re.search(r'\b[A-Za-z_][A-Za-z0-9_]*\b', b_txt):
                    continue

                if b_txt == m_txt:
                    continue

                # ⇒ try implication forms
                try:
                    res.append(make_implies(b, m))
                    res.append(make_implies(make_unop("!", b), m))
                except Exception as e:
                    print(f"⚠️ Failed to create implication: {e}")

        # final dedup + tautology skip + NEW “constant-LHS skip”
        seen = set()
        uniq = []
        for r in res:
            if r is None:
                continue

            t = r.text() if hasattr(r, "text") else str(r)

            if "==>" in t:
                try:
                    lhs_txt, rhs_txt = [s.strip() for s in t.split("==>", 1)]

                    # ❌ skip tautologies
                    if lhs_txt == rhs_txt:
                        continue

                    # ❌ NEW: skip implications whose LHS is constant-only
                    # (e.g., “1 <= -1 ==> m” or “true ==> m”)
                    if not re.search(r'\b[A-Za-z_][A-Za-z0-9_]*\b', lhs_txt):
                        continue

                except Exception:
                    pass

            if t not in seen:
                seen.add(t)
                uniq.append(r)

        return uniq


    # ------------------------------------------------------------------
    # Helper to get "all five families" in one call
    # ------------------------------------------------------------------
    def five_family_mutations(self, int_subs=1, aging_subs=1, scalar_limit=100):
        """
        Convenience wrapper that collects candidates corresponding to
        the 5 mutation families described in the paper:

          1. Variable substitutions          (variable_substitution_mutations)
          2. Boundary adjustments           (mutations_and_aging + literal shifts)
          3. Constraint relaxations         (constraint_relaxation_mutations)
          4. Quantifier instantiation       (quantifier_instantiation_mutations)
          5. Conditional splitting / guards (conditional_splitting_mutations
                                             + predicate/boolean-based implies)

        plus the existing scalar and predicate-based generators.
        """
        res = []

        # 1 + 2: scalar substitutions & aging / boundary tweaks
        res += self.variable_substitution_mutations(int_subs)
        res += self.mutations_and_aging(int_subs, aging_subs)
        res += self.boundary_adjustment_mutations()

        # 3: relax comparisons
        res += self.constraint_relaxation_mutations()

        # 4: quantifier instantiation
        res += self.quantifier_instantiation_mutations()

        # 5: conditional splitting and implication-style invariants
        res += self.conditional_splitting_mutations()
        res += self.boolean_mutations()
        res += self.predicate_mutations()
        res += self.scalar_mutations(max_mutations=scalar_limit)

        # final dedup
        seen = set()
        uniq = []
        for e in res:
            if e is None:
                continue
            t = e.text() if hasattr(e, "text") else str(e)
            if t not in seen:
                seen.add(t)
                uniq.append(e)
        if DEBUG_MUTATOR:
            print(f"✅ five_family_mutations produced {len(uniq)} unique candidates")
        return uniq

    # ------------------------------------------------------------------
    # Remaining helper methods (unchanged)
    # ------------------------------------------------------------------
    def add_parametric_calls(self, n):
        if n >= 0:
            old_arity = self.method.arity
            self.method.set_arity(n)
        raw_ints = self.method.get_ints()
        self.method_ints = [e for e in raw_ints if self._is_scalar_int_expr(e)]
        self.method.set_arity(old_arity)

    def add_constant_expression(self, exp):
        if isinstance(exp, str) and exp.strip():
            e = qp(exp)
            if e and self._is_scalar_int_expr(e):
                self.method_ints.append(e)

    def keep_only(self, exp):
        self.method.ints = []
        for e in exp.split(","):
            parsed = qp(e.strip())
            if parsed and self._is_scalar_int_expr(parsed):
                self.method.ints.append(parsed)
        raw_ints = self.method.get_ints()
        self.method_ints = [e for e in raw_ints if self._is_scalar_int_expr(e)]

    def suggest(self, pred, more=1):
        ts = [self.theories[tn] for tn in self.theories if any(p.text().find(tn + ".") != -1 for p in self.posts)]
        suggestions = []
        for p in PredicateExtractor(parseString(pred + ";")):
            if len(p.args) > 1:
                suggestions.append([a.text() for a in p.args[1:]])
        for sug in suggestions:
            for t in ts:
                self.active_preds += t.get_bools(
                    n=len(sug) + more,
                    obj="",
                    base=self.method_ints,
                    refs=self.method.get_refs(),
                    fixedArgs=sug,
                )
        self.instantiated = True

    def activate_theory_from_post(self, n=3):
        ps = []
        for p in self.posts:
            try:
                extracted = PredicateExtractor(p)
                if extracted:
                    ps.extend([e for e in extracted if e is not None])
            except Exception:
                continue
        args_list = []
        for pred in ps:
            if hasattr(pred, "args") and len(pred.args) > 1:
                args = [a.text() for a in pred.args[1:] if a is not None]
                args_list.append(args)
        ts = [self.theories[tn] for tn in self.theories if any(p and p.text().find(tn + ".") != -1 for p in self.posts)]
        for args in args_list:
            for t in set(ts):
                try:
                    new_preds = t.get_bools(
                        n=n, obj="", base=self.method_ints, refs=self.method.get_refs(), fixedArgs=args,
                    )
                    self.active_preds += new_preds
                except Exception:
                    pass
        self.instantiated = True

    def activate_post_expressions(self):
        ps = []
        for p in self.posts:
            try:
                for e in PredicateExtractor(p):
                    if e is not None and self._is_scalar_int_expr(e):
                        ps.append(e)
            except Exception:
                continue
        seen = set()
        uniq = []
        for e in ps:
            t = e.text()
            if t not in seen:
                seen.add(t)
                uniq.append(e)
        self.method_ints += uniq

    def activate_post_predicates(self):
        ps = []
        for p in self.posts:
            try:
                extracted = PredicateExtractor(p)
                valid_preds = [e for e in extracted if e is not None]
                ps.extend(valid_preds)
            except Exception:
                continue
        self.active_preds += list(set(ps))

    def add_distance_expressions(self, positive=False):
        scalars = [e for e in self.method_ints if self._is_scalar_int_expr(e)]
        pairs = [(x, y) for x in scalars for y in scalars if x != y]
        for x, y in pairs:
            expr = make_binop("+" if positive else "-", x, y)
            if self._is_scalar_int_expr(expr):
                self.method_ints.append(expr)

    def add_oldless_post(self):
        oldless = []
        for p in self.posts:
            new_p = qp(p.text().replace("\\old", ""))
            if new_p and new_p.text() != p.text():
                oldless.append(new_p)
        self.posts += oldless

    def add_old(self, n=1):
        old = []
        for p in self.posts:
            old += substitute_all(p, [p], n, "OldAdder")
        self.posts += old

    def add_resultless_post(self):
        resultless = []
        for p in self.posts:
            resultless.extend(ResultRemover(p))
        self.posts += resultless

    def activate_theory_predicates(self, n=3):
        ts = [t for name, t in self.theories.items() if any(p.text().find(name + ".") != -1 for p in self.posts)]
        for t in ts:
            self.active_preds += t.get_bools(n=n, obj="", base=self.method_ints, refs=self.method.get_refs())
        self.instantiated = True

    def activate_weakening_predicates(self, max_pairs=200):
        scalars = [e for e in self.method_ints if self._is_scalar_int_expr(e)]
        pairs = []
        for x in scalars:
            for y in scalars:
                if x is y:
                    continue
                pairs.append((x, y))
                if len(pairs) >= max_pairs:
                    break
            if len(pairs) >= max_pairs:
                break
        for x, y in pairs:
            self.weakening_preds.append(make_binop("<=", x, y))
            self.weakening_preds.append(make_binop("!=", x, y))

    def scalar_mutations(self, max_mutations=100):
        res = []
        bools = [b for b in (self.weakening_preds + self.method.get_bools()) if b is not None]
        scalars = [e for e in self.method_ints if self._is_scalar_int_expr(e)]
        pairs = [(x, y) for x in scalars for y in scalars if x is not None and y is not None and x is not y]
        cmp_ops = ("<", "<=", "==")
        for b in bools:
            for l, r in pairs:
                for op in cmp_ops:
                    try:
                        rhs = make_binop(op, l, r)
                        mut = make_implies(b, rhs)
                        res.append(mut)
                        if len(res) >= max_mutations:
                            return res
                    except Exception:
                        continue
        return res

        # ------------------------------------------------------------------
    # ✅ Paper-official five mutation strategies only
    # ------------------------------------------------------------------
    def paper_five_mutations(self, int_subs=1, aging_subs=1, scalar_limit=100):
        """
        Only the five mutation families described in the paper:
        1. Basic variable substitutions
        2. Post-predicate implications
        3. Boolean mutations
        4. Scalar weakening
        5. Aging adjustments (+/-1)
        Other mutation families remain defined in code but are not invoked here.
        """
        res = []

        # ensure base predicates and refs are active
        self.activate_post_expressions()
        self.activate_post_predicates()
        self.activate_theory_predicates()
        self.activate_weakening_predicates()

        # 1️⃣ basic variable substitutions
        basic = self.mutations(int_subs)
        if DEBUG_MUTATOR:
            print(f"✅ Strategy basic generated {len(basic)} mutations")
        res += basic

        # 2️⃣ post_predicate implications
        post_pred = self.predicate_mutations(n=int_subs)
        if DEBUG_MUTATOR:
            print(f"✅ Strategy post_pred generated {len(post_pred)} mutations")
        res += post_pred

        # 3️⃣ boolean mutations
        boolean = self.boolean_mutations(n=int_subs)
        if DEBUG_MUTATOR:
            print(f"✅ Strategy boolean generated {len(boolean)} mutations")
        res += boolean

        # 4️⃣ scalar inequalities
        scalar = self.scalar_mutations(max_mutations=scalar_limit)
        if DEBUG_MUTATOR:
            print(f"✅ Strategy scalar generated {len(scalar)} mutations")
        res += scalar

        # 5️⃣ aging (+/-1 variants)
        aging = self.mutations_and_aging(n=int_subs, n_age=1)
        if DEBUG_MUTATOR:
            print(f"✅ Strategy aging generated {len(aging)} mutations")
        res += aging

        # final deduplication
        seen = set()
        uniq = []
        for e in res:
            if e is None:
                continue
            t = e.text() if hasattr(e, "text") else str(e)
            if t not in seen:
                seen.add(t)
                uniq.append(e)

        if DEBUG_MUTATOR:
            print(f"✅ paper_five_mutations produced {len(uniq)} unique total candidates")

        return uniq

    