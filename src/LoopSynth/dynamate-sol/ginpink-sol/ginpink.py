import os
import re
from SolidityAST import make_binop, make_unop, make_implies  # Assuming utility functions for AST nodes
from SolidityInvariantParser import SolidityInvariantParser
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

# Directory where Solidity contract files are stored
SOLIDITY_CONTRACTS_DIR = ''
EXTENSION = ".info"

def read_contract(contract_name, location='.'):
    """
    Reads and parses a Solidity .info metadata file (theory-style), similar to GIN-DYN's read_class.
    Returns a SolPinkTheory object directly.
    """
    filepath = os.path.join(location, contract_name + EXTENSION)

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
        elif line == "== Package ==":
            in_pkg = True
            in_ints = False
            in_bools = False
        elif line == "== Integer expressions ==":
            in_pkg = False
            in_ints = True
            in_bools = False
        elif line == "== Boolean expressions ==":
            in_pkg = False
            in_ints = False
            in_bools = True
        elif in_pkg:
            pkg = line
        elif in_ints:
            int_expressions.append(line)
        elif in_bools:
            bool_expressions.append(line)

    # Return a single SolPinkTheory object
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

    for cl in lines:
        print("Parsed line →", repr(cl))
        print(f"    Flags: pre={in_pre}, post={in_post}, invs={in_invs}, cmd={in_cmd}")
        if cl == '' or cl.startswith('//'):
            continue
        elif cl == '== Package ==':
            in_pkg, in_method, in_static = True, False, False
            in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical
        elif cl.strip() == '== Method ==':
            print("📌 ENTERING Method Section")
            # flush previous method
            if name:
                print(f"🧩 Appending method '{name}' with {len(posts)} postconditions")
                ms.append((name, static, ints, bools, refs, posts, invs, cmds, pres))

            # reset everything
            name = ''
            static = False
            ints = []
            bools = []
            refs = {}
            pres = []
            posts = []
            invs = []
            cmds = []
            in_method = True  # <== moved here
            in_pkg = in_static = in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical

        elif cl == '== Static ==':
            in_static = True
            in_pkg = in_method = in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical
        elif cl == '== Integer expressions ==':
            in_ints = True
            in_pkg = in_method = in_static = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical
        elif cl == '== Boolean expressions ==':
            in_bools = True
            in_pkg = in_method = in_static = in_ints = in_refs = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical
        elif cl == '== Ref expressions ==':
            in_refs = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_pre = in_post = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical
        elif cl.strip() == '== Preconditions ==':
            print("📌 ENTERING Precondition Section")
            in_pre = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_post = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical

        elif cl.strip() == '== Postconditions ==':
            print("📌 ENTERING Postcondition Section")
            in_post = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_pre = in_invs = in_cmd = False
            in_templates = False  # ✅ this is critical

        elif cl.strip() == '== Invariants ==':
            print("📌 ENTERING Invariant Section")
            in_invs = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_post = in_pre = in_cmd = False
            in_templates = False  # ✅ this is critical

        elif cl.strip() == '== Commands ==':
            print("📌 ENTERING Commands Section")
            in_cmd = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_post = in_pre = in_invs = False
            in_templates = False  # ✅ this is critical
        elif cl == '== Template boolean expressions ==':
            in_templates = True
            in_pkg = in_method = in_static = in_ints = in_bools = in_refs = in_pre = in_post = in_invs = in_cmd = False
        elif in_templates:
            template_bools.append(cl)  # Don't parse — just store raw        
        elif in_pkg:
            pkg = cl
        elif in_method:
            name = cl
            in_method = False  # ✅ mark method name as captured
        elif in_static:
            static = (cl == 'Y')
        elif in_ints:
            ints.append(cl)
        elif in_bools:
            bools.append(cl)
        elif in_refs:
            if ':' in cl:
                key, ids = cl.split(':', 1)
                refs[key.strip()] = [i.strip() for i in ids.split(',')]
        elif in_pre:
            pres.append(cl)
        elif in_post:
            print(f"➕ Adding postcondition line: {repr(cl)}")
            posts.append(cl)
        elif in_invs:
            invs.append(cl)
        elif in_cmd:
            cmds.append([x.strip() for x in cl.split(';')])

    # ✅ Append the last method (if any)
    if name:
        print(f"🧩 Final append of method '{name}' with {len(posts)} posts")
        ms.append((name, static, ints, bools, refs, posts, invs, cmds, pres))

        # 🧼 Reset all per-method accumulators (to avoid bleed-over or reuse)
        name = ''
        static = False
        ints = []
        bools = []
        refs = {}
        pres = []
        posts = []
        invs = []
        cmds = []
    
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

        parsed_pres = []
        for p in m[8]:
            try:
                e = parse_expr(p.strip().rstrip(';'))
                if e:
                    parsed_pres.append(e)
            except Exception as ex:
                print(f"[ERROR] Failed to parse precondition: {p} → {ex}")

        parsed_posts = []

        print(f"🧾 Raw m[5] (postconditions list): {m[5]}")
        for p in m[5]:  # Postconditions
            cleaned = p.strip().rstrip(';')
            print(f"🧪 Trying to parse postcondition: '{cleaned}'")
            try:
                e = parse_expr(cleaned)
                if e:
                    e.cur_pos = True
                    print(f"🔬 Raw expr: {p.strip()} → Parsed: {e.text()}")
                    print(f"🔍 Result: {e} (type={type(e)})")
                    parsed_posts.append(e)
                    print(f"✅ Appended postcondition: {e.text()}")
                    
                    # ✅ ADD THIS:
                    print(f"📊 Total postconditions so far: {len(parsed_posts)}")
                    for idx, post in enumerate(parsed_posts, 1):
                        print(f"   🔹 [{idx}] {post.text()}")
                else:
                    print(f"⚠️ parse_expr returned None for: '{cleaned}'")
            except Exception as ex:
                print(f"❌ Exception while parsing postcondition: '{cleaned}' → {ex}")


        parsed_invs = []
        for p in m[6]:
            try:
                e = parse_expr(p.strip().rstrip(';'))
                if e:
                    parsed_invs.append(e)
            except Exception as ex:
                print(f"[ERROR] Failed to parse invariant: {p} → {ex}")

        result.append((method_obj, parsed_posts, parsed_invs, parsed_pres))
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
    # Parse root if needed
    if isinstance(root_expr_or_node, str):
        root = parse_expr(root_expr_or_node)
        if not root:
            print(f"❌ Failed to parse root expression: '{root_expr_or_node}'")
            return []
    else:
        root = root_expr_or_node

    root.cur_pos = True  # Enable substitution tracking
    print(f"🔍 Substituting in: '{root.text()}'")
    print(f"🧩 Using {len(exprs)} expressions: {[e.text() for e in exprs if e]}")

    result = []
    for d in range(n + 1):
        print(f"🔁 Substitution pass with depth {d}")
        try:
            partial = substitute(root, exprs, d, sub_class_name)
            print(f"✅ Depth {d} → {len(partial)} substitutions")
            result.extend(partial)
        except Exception as ex:
            print(f"❌ Error during substitution at depth {d}: {ex}")

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
            arg_count = expr.count('#')
            if arg_count not in grouped:
                grouped[arg_count] = []
            grouped[arg_count].append(expr)
        return grouped

    def get_ints(self, obj='', n=0, base=[]):
        results = []

        for m in range(n + 1):
            if m in self.ints:
                for expr in self.ints[m]:
                    expr = expr.strip()
                    if not expr or expr.endswith('.'):
                        continue  # 🚫 Skip malformed base expressions

                    if "$" in expr:
                        updated_expr = expr.replace("$", obj)
                    elif obj and not any(sym in expr for sym in [".", "(", "["]):
                        updated_expr = f"{obj}.{expr}"
                    else:
                        updated_expr = expr

                    substituted = substitute_all(updated_expr, base, m, "substitute_expressions")

                    for s in substituted:
                        try:
                            parsed = parse_expr(s)
                            if parsed:
                                text = parsed.text().strip()
                                if not text.endswith("."):
                                    results.append(parsed)
                                else:
                                    print(f"🚫 Skipping invalid substituted expr: '{text}'")
                        except Exception as ex:
                            print(f"❌ parse_expr failed for: '{s}' → {ex}")

        return results

    def get_bools(self, obj='', n=0, base=[], refs=[], fixedArgs=[]):
        """
        Retrieves boolean expressions, supporting argument substitution.
        Returns parsed ASTs instead of plain strings.
        """
        results = []
        prefix = f"{obj}." if obj else ""

        for m in range(n + 1):
            if m in self.bools:
                for expr in self.bools[m]:
                    for ref in refs:
                        # Replace $ with reference
                        new_expr = expr.replace("$", ref)

                        # Replace each # with fixed argument
                        for arg in fixedArgs:
                            new_expr = new_expr.replace("#", arg, 1)

                        # Substitution of remaining # with base expressions
                        remaining_subs = max(0, m - len(fixedArgs))
                        substituted_exprs = substitute_all(new_expr, base, remaining_subs, "substitute_expressions")

                        # ✅ Parse to ASTs
                        for s in substituted_exprs:
                            if "ZZZZ" not in s:  # Filter out bad substitutions
                                parsed = parse_expr(s)
                                if parsed:
                                    results.append(parsed)

        return results

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
            for parsed in [parse_expr(e)] if parsed
        ]
        self.bools = [parse_expr(e) for e in boollist if parse_expr(e)]

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

    def __init__(self, method, theories, posts):
        self.method = method
        self.theories = {t.name: t for t in theories}

        # ✅ Use already parsed ASTs (no re-parsing)
        self.posts = [p for p in posts if p is not None]

        for post in self.posts:
            # If it's a MethodCall, fix the args
            if hasattr(post, "args") and isinstance(post.args, list):
                post.args = [convert_parser_expr(arg) for arg in post.args]

        self.method_ints = self.method.get_ints()
        self.active_preds = []
        self.weakening_preds = []
        self.instantiated = False

    def mutations(self, n=1):
        print("🧪 Running `mutations()`")
        print(f"🔍 Posts: {[p.text() for p in self.posts]}")
        print(f"🔍 Method ints: {[i.text() for i in self.method_ints]}")
        
        res = []
        for p in self.posts:
            m = substitute_all(p, self.method_ints, n, "IntSubstitutions")
            print(f"🔁 Substituting on: {p.text()} → {len(m)} mutations")
            res += m
        return res

    def mutations_and_aging(self, n=1, n_age=1):
        bm = self.mutations(n)
        aging_plus = parse_expr("+1")
        aging_minus = parse_expr("-1")
        res = []
        for m in bm:
            res += substitute_all(m, [aging_plus, aging_minus], n_age, "AgingSubstitutions")
        return bm + res

    def boolean_mutations(self, n=1):
        unneg = []
        if not self.instantiated:
            for p in self.active_preds:
                unneg += substitute_all(p, self.method_ints, n, "IntSubstitutions")
        else:
            unneg = self.active_preds

        neg = [make_unop("!", m) for m in unneg]
        muts = unneg + neg

        res = []
        for p in self.posts:
            res += substitute_all(p, muts, n, "BooleanSubstitutions")
        return res

    def predicate_mutations(self, n=1, more=0, variants=True):
        """
        Performs predicate-level boolean mutations with (optional) implication chaining.
        Uses active predicates substituted with method integers to produce implications.
        Safely handles None values and reports issues gracefully.
        """
        unneg = []

        # ✅ Safely substitute all predicates using method integers
        try:
            if not self.instantiated:
                for p in self.active_preds:
                    if p is not None:
                        unneg += substitute_all(p, self.method_ints, n, "IntSubstitutions")
            else:
                for p in self.active_preds:
                    if p is not None:
                        unneg += substitute_all(p, self.method_ints, more, "IntSubstitutions")
        except Exception as e:
            print(f"⚠️ Error during predicate substitution: {e}")

        # If no chaining requested, return only positive/negative forms
        if not variants:
            return [u for u in unneg if u is not None]

        # ✅ Generate negations (skip None)
        neg = [make_unop("!", m) for m in unneg if m is not None]
        muts = [m for m in unneg if m is not None] + neg

        res = []

        # ✅ Get boolean expressions from method and weakening_preds, filtered
        bools = [b for b in (self.weakening_preds + self.method.get_bools()) if b is not None]

        for m in muts:
            if m is None:
                continue
            for b in bools:
                if b is None:
                    continue
                try:
                    res.append(make_implies(b, m))
                    res.append(make_implies(make_unop("!", b), m))
                except Exception as e:
                    b_txt = b.text() if hasattr(b, 'text') else str(b)
                    m_txt = m.text() if hasattr(m, 'text') else str(m)
                    print(f"⚠️ Failed to create implication between {b_txt} and {m_txt}: {e}")

        # ✅ Final cleanup of any accidental Nones
        return [r for r in res if r is not None]

    def add_parametric_calls(self, n):
        if n >= 0:
            old_arity = self.method.arity
            self.method.set_arity(n)
        self.method_ints = self.method.get_ints()
        self.method.set_arity(old_arity)

    def add_constant_expression(self, exp):
        if isinstance(exp, str) and exp.strip():
            e = parse_expr(exp)
            if e:
                self.method_ints.append(e)

    def keep_only(self, exp):
        self.method.ints = []
        for e in exp.split(","):
            parsed = parse_expr(e.strip())
            if parsed:
                self.method.ints.append(parsed)

    def suggest(self, pred, more=1):
        ts = [self.theories[tn] for tn in self.theories if any(p.text().find(tn + ".") != -1 for p in self.posts)]
        suggestions = []

        for p in PredicateExtractor(parseString(pred + ";")):
            if len(p.args) > 1:
                suggestions.append([a.text() for a in p.args[1:]])

        for sug in suggestions:
            for t in ts:
                self.active_preds += t.get_bools(n=len(sug)+more, obj="", base=self.method_ints,
                                                 refs=self.method.get_refs(), fixedArgs=sug)

        self.instantiated = True

    def activate_theory_from_post(self, n=3):
        ps = []
        for p in self.posts:
            try:
                extracted = PredicateExtractor(p)
                if extracted:
                    ps.extend([e for e in extracted if e is not None])
            except Exception as ex:
                post_text = p.text() if hasattr(p, "text") else str(p)
                print(f"⚠️ Predicate extraction failed for: '{post_text}' → {ex}")

        args_list = []
        for pred in ps:
            try:
                if hasattr(pred, "args") and len(pred.args) > 1:
                    args = [a.text() for a in pred.args[1:] if a is not None]
                    args_list.append(args)
            except Exception as ex:
                print(f"⚠️ Argument extraction failed for predicate: {pred} → {ex}")

        ts = [self.theories[tn] for tn in self.theories if any(p and p.text().find(tn + ".") != -1 for p in self.posts)]

        for args in args_list:
            for t in set(ts):
                try:
                    new_preds = t.get_bools(n=n, obj="", base=self.method_ints,
                                            refs=self.method.get_refs(), fixedArgs=args)
                    self.active_preds += new_preds
                except Exception as ex:
                    print(f"⚠️ Failed to get booleans from theory '{t.name}' with args {args} → {ex}")

        self.instantiated = True

    def activate_post_expressions(self):
        ps = []
        for p in self.posts:
            ps.extend(PredicateExtractor(p))
        self.method_ints += list(set(ps))

    def activate_post_predicates(self):
        """
        Extracts predicates from postconditions and stores them in self.active_preds.
        Ensures None values are filtered and extraction failures are logged.
        """
        ps = []
        for p in self.posts:
            try:
                extracted = PredicateExtractor(p)
                # Filter out None and avoid duplicates
                valid_preds = [e for e in extracted if e is not None]
                ps.extend(valid_preds)

                # Optional debug log
                print(f"📌 Extracted {len(valid_preds)} predicates from post: {p.text()}")
                for i, pred in enumerate(valid_preds, 1):
                    print(f"  ✅ Predicate #{i}: {pred.text()}")
            except Exception as ex:
                try:
                    p_text = p.text()
                except Exception:
                    p_text = str(p)
                print(f"⚠️ Predicate extraction failed for: '{p_text}' → {ex}")

        self.active_preds += list(set(ps))

    def add_distance_expressions(self, positive=False):
        pairs = [(x, y) for x in self.method_ints for y in self.method_ints if x != y]
        for x, y in pairs:
            expr = make_binop("+" if positive else "-", x, y)
            self.method_ints.append(expr)

    def add_oldless_post(self):
        oldless = []
        for p in self.posts:
            new_p = parse_expr(p.text().replace("\\old", ""))
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

    def activate_weakening_predicates(self):
        pairs = [(x, y) for x in self.method_ints for y in self.method_ints if x != y]
        for x, y in pairs:
            self.weakening_preds.append(make_binop("<=", x, y))
            self.weakening_preds.append(make_binop("!=", x, y))

    def scalar_mutations(self, max_mutations=100):
        """
        Applies scalar mutations by generating implications between weakening predicates
        and integer expression pairs. Caps output to avoid combinatorial explosion.
        
        :param max_mutations: Maximum number of mutations to generate.
        :return: List of mutated expressions.
        """
        res = []
        bools = self.weakening_preds + self.method.get_bools()
        pairs = [(x, y) for x in self.method_ints for y in self.method_ints if x != y]

        for b in bools:
            for l, r in pairs:
                try:
                    res.append(make_implies(b, make_binop("<", l, r)))
                    if len(res) >= max_mutations:
                        return res
                    res.append(make_implies(b, make_binop("+", l, r)))
                    if len(res) >= max_mutations:
                        return res
                except Exception as e:
                    b_txt = b.text() if hasattr(b, 'text') else str(b)
                    l_txt = l.text() if hasattr(l, 'text') else str(l)
                    r_txt = r.text() if hasattr(r, 'text') else str(r)
                    print(f"⚠️ Failed to create scalar mutation: {b_txt}, {l_txt}, {r_txt} → {e}")

        return res
