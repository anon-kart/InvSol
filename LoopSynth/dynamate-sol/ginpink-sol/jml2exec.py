#!/usr/bin/python

import argparse
import copy
import sys
from solidity_ast import *  # Solidity AST parser
from solidity_parser import parse_expression  # Function to parse Solidity expressions
from substitution import Substitutions  # Handles expression substitutions

class SolidityInvariantTransformer(Substitutions):
    """
    Transforms Solidity loop invariants into executable Solidity assertions.
    """
    errors = []

    def __init__(self, expression, root):
        super(SolidityInvariantTransformer, self).__init__(expression, root)
        self.failed = False

    def transform_expression(self, target, call, args):
        """
        Transforms expressions by removing unnecessary Solidity type conversions and 
        handling known function calls related to mathematical comparisons.
        """
        known_calls = ["lt", "lte", "gt", "gte", "eq", "neq"]
        res = [a.text() for a in args]

        # ✅ Handling multiple Solidity libraries (SafeMath, OpenZeppelin, etc.)
        allowed_libraries = ["SafeMath", "Math", "Ownable"]
        
        if target in allowed_libraries and call in known_calls:
            for i in range(len(args)):
                res[i] = res[i].replace(".toUint256()", "").replace(".toInt256()", "").replace(".toUint8()", "")
                args[i] = parse_expression(res[i] + ";")
                assert args[i] is not None

    def FunctionCall_visit(self, node):
        """
        Visits function calls and applies necessary transformations.
        """
        super(SolidityInvariantTransformer, self).FunctionCall_visit(node)
        if node.target is not None:
            target = node.target.text()
            if node.call is not None:
                call = ".".join([c.text() for c in node.call])
                self.transform_expression(target, call, node.args)


# ✅ Trivial Invariant Removal
class SolidityRemoveTrivial(Substitutions):
    """
    Sets `self.trivial = True` if all method calls are trivial, and at least one theory predicate exists.
    """
    trivial = None
    theory_preds = 0
    _in_pred = None

    def __init__(self, expression, strict=True):
        super(SolidityRemoveTrivial, self).__init__(expression, None)
        self.trivial = False
        self._in_pred = False
        self.theory_preds = 0 if strict else 1
        self.nexp.accept(self)
        if self.theory_preds == 0:
            self.trivial = True

    def MethodCall_visit(self, node):
        """
        Visits method calls and detects trivial cases.
        """
        if is_theorypred(node):
            self.theory_preds += 1
            is_theory = True
        else:
            is_theory = False
        old_in_pred = self._in_pred
        if self._in_pred:
            if is_theory:
                self.trivial = True  # No nested theory predicates allowed
                return
        else:
            self._in_pred = True
        super(SolidityRemoveTrivial, self).MethodCall_visit(node)
        self._in_pred = old_in_pred
        if not self.trivial:
            self.trivial = is_trivial(node)

# ✅ Replacing Method Names
class SolidityReplaceNames(Substitutions):
    """
    Replaces method names using a predefined mapping (`fullNamesMapping`).
    """
    fullNamesMapping = None
    result = None

    def __init__(self, expression, fullNamesMapping):
        expr_copy = copy.deepcopy(expression)
        super(SolidityReplaceNames, self).__init__(expr_copy, expr_copy)
        self.fullNamesMapping = fullNamesMapping
        self.fullNamesMapping["SafeMath"] = "Math"
        self.fullNamesMapping["SafeMath.add"] = "Math.safeAdd"
        self.fullNamesMapping["SafeMath.sub"] = "Math.safeSub"
        expr_copy.accept(self)
        self.result = expr_copy

    def MethodCall_visit(self, node):
        """
        Visits method calls and replaces names using `fullNamesMapping`.
        """
        super(SolidityReplaceNames, self).MethodCall_visit(node)
        if node.target is not None:
            target = node.target.text()
            if target in self.fullNamesMapping:
                node.target = parse_expression(self.fullNamesMapping[target] + ";")

# ✅ Detecting Trivial and Theory Predicates
def is_trivial(mcall):
    if len(mcall.call) != 1 or mcall.args is None:
        return False
    call = mcall.call[0].text()
    target = mcall.target.text()
    args = [a.text() for a in mcall.args]
    return target in SolidityPredicateExpansion.triviality and call in SolidityPredicateExpansion.triviality[target] and SolidityPredicateExpansion.triviality[target][call](args)

def is_theorypred(mcall):
    """
    Checks if a method call is a theory predicate.
    """
    target = mcall.target.text()
    return target in SolidityPredicateExpansion.triviality

class SolidityExecutableInvariant(object):
    """
    Converts Solidity loop invariants into executable assertions.
    """
    original_node = None
    node = None
    errors = None

    def __init__(self, solidity_expression, parsed=False):
        self.errors = []
        if parsed:
            self.original_node = solidity_expression
        else:
            self.original_node = parse_expression(solidity_expression)
        self.node = self.original_node

    def get_text(self):
        return self.node.text() if self.node else ""

    def is_executable(self):
        """
        Checks if the Solidity invariant can be executed as a require/assert statement.
        """
        if self.node is None:
            return False
        try:
            t = self.node.text()
            # ✅ Improved check to match Dynamate: reject untransformed expressions
            if "\\forall" in t or "\\old" in t or "\\result" in t or "==>" in t:
                return False
            return "require(" in t or "assert(" in t
        except:
            return False

    def make_executable(self):
        """
        Transforms Solidity loop invariants into Solidity assertions.
        """
        if self.is_executable():
            return

        t = self.original_node.text()

        # ✅ Reject expressions containing `\result`
        if "\\result" in t:
            self.node = None
            self.errors.append("❌ Solidity does not support \\result expressions.")
            return

        # ✅ Apply main transformations
        transformer = SolidityExecutableSubstitution(self.node, self.node)
        self.node.accept(transformer)
        self.errors = transformer.errors

        # ✅ Final syntactic cleanup of `\old(x)` → `old_x`
        if not self.is_executable():
            try:
                ns = self.node.text().replace("\\old(", "(old_")
                self.node = parse_expression(ns + ";")
                self.errors.append("⚠️ Final pass: replaced remaining \\old expressions.")
            except:
                self.errors.append("❌ Corrupted node: could not make executable.")

    def make_quantification(self, integer_arrays=True, preconditions=False):
        """
        Expands quantifiers (`forall`, `exists`) into explicit Solidity loops or mappings.
        """
        pe = SolidityPredicateExpansion(self.node, self.node)
        if not integer_arrays:
            pe.use_int_arrays()
        if preconditions:
            pe.use_preconditions()
        self.node.accept(pe)
        self.errors = pe.errors

        if pe.failed:
            return False

        if isinstance(self.node, MethodCall) and self.node._sub is not None:
            self.node = self.node._sub

        # ✅ Convert conditional expressions back into implications (A ? B : true → A ⇒ B)
        if isinstance(self.node, ConditionalExpression) and self.node.else_exp.text() == "true":
            impl = ImpliesExpression()
            impl.left = self.node.condition
            impl.right = self.node.then_exp
            self.node = impl

        return True


class SolidityQuantifierExpansion(Substitutions):
    """
    Expands quantifiers (forall, exists) to explicit Solidity loops or mappings.
    """
    errors = []

    def __init__(self, expression, root):
        super(SolidityQuantifierExpansion, self).__init__(expression, root)
        self.failed = False

    def expand_quantifiers(self, node):
        """
        Expands \forall and \exists expressions into Solidity loops.
        """
        if "\\forall" in node.text():
            # ✅ Convert universal quantifier to a loop
            loop_var = "i"
            condition = node.text().replace("\\forall", "").strip()
            replacement = f"""
                bool allTrue = true;
                for (uint {loop_var} = 0; {loop_var} < arr.length; {loop_var}++) {{
                    if (!({condition})) {{
                        allTrue = false;
                        break;
                    }}
                }}
                require(allTrue, "Invariant failed");
            """
            node._sub = parse_expression(replacement)
        elif "\\exists" in node.text():
            # ✅ Convert existential quantifier to a loop with early exit
            loop_var = "i"
            condition = node.text().replace("\\exists", "").strip()
            replacement = f"""
                bool exists = false;
                for (uint {loop_var} = 0; {loop_var} < arr.length; {loop_var}++) {{
                    if ({condition}) {{
                        exists = true;
                        break;
                    }}
                }}
                require(exists, "Invariant failed");
            """
            node._sub = parse_expression(replacement)

    def QuantifiedExpression_visit(self, node):
        """
        Visits quantified expressions and applies transformations.
        """
        super(SolidityQuantifierExpansion, self).QuantifiedExpression_visit(node)
        self.expand_quantifiers(node)


class SolidityTrivialityCheck(Substitutions):
    """
    Detects trivial invariants (e.g., x == x) and removes them.
    """
    trivial = None

    def __init__(self, expression):
        super(SolidityTrivialityCheck, self).__init__(expression, None)
        self.trivial = False
        self.nexp.accept(self)

    def is_trivial(self, node):
        """
        Identifies trivial invariants.
        """
        if "==" in node.text():
            left, right = node.text().split("==")
            return left.strip() == right.strip()
        return False

    def BinaryExpression_visit(self, node):
        """
        Visits binary expressions and removes trivial cases.
        """
        super(SolidityTrivialityCheck, self).BinaryExpression_visit(node)
        if self.is_trivial(node):
            self.trivial = True

class SolidityPredicateExpansion(Substitutions):
    """
    Expands Solidity predicates into executable Solidity assertions.
    """
    errors = []

    def __init__(self, expression, root):
        super(SolidityPredicateExpansion, self).__init__(expression, root)
        self.failed = False

    # ✅ Precondition Expansion for Solidity
    precondition_predicates = {
        "SolArrays": {
            "sorted": lambda a, fromIndex, toIndex: 
                f"require({a} != address(0) && {fromIndex} >= 0 && {fromIndex} <= {toIndex} && {toIndex} <= {a}.length, 'Array constraints failed');",
            "exists": lambda a, fromIndex, toIndex, key: 
                f"require({a} != address(0) && {fromIndex} >= 0 && {fromIndex} <= {toIndex} && {toIndex} <= {a}.length, 'Key existence check failed');"
        }
    }

    # ✅ Expansion for Integer Arrays (`forall`, `exists`)
    precondition_Integer_predicates = {
        "SolArrays": {
            "sorted": lambda a, fromIndex, toIndex: 
                f"for (uint i = {fromIndex}; i < {toIndex}; i++) require({a}[i] <= {a}[i+1], 'Array not sorted');",
            "exists": lambda a, fromIndex, toIndex, key: 
                f"bool found = false; for (uint i = {fromIndex}; i < {toIndex}; i++) if ({a}[i] == {key}) found = true; require(found, 'Key not found');"
        }
    }

    # ✅ Postcondition Mutation (`pred2post`)
    pred2post = {
        "SolArrays": {
            "sorted": lambda a, fromIndex, toIndex: 
                f"for (uint i = {fromIndex}; i < {toIndex} - 1; i++) require({a}[i] <= {a}[i+1], 'Postcondition failed: Array not sorted');",
            "exists": lambda a, fromIndex, toIndex, key: 
                f"bool exists = false; for (uint i = {fromIndex}; i < {toIndex}; i++) if ({a}[i] == {key}) exists = true; require(exists, 'Postcondition failed: Key not found');"
        }
    }

    # ✅ Binary Expression Handling
    def BinaryExpression_visit(self, node):
        """
        Expands method calls inside binary expressions.
        """
        super(SolidityPredicateExpansion, self).BinaryExpression_visit(node)
        if isinstance(node.left, MethodCall) and node.left._sub is not None:
            node.left = node.left._sub
        if isinstance(node.right, MethodCall) and node.right._sub is not None:
            node.right = node.right._sub

    # ✅ Unary Expression Handling
    def UnaryExpression_visit(self, node):
        """
        Expands method calls inside unary expressions.
        """
        super(SolidityPredicateExpansion, self).UnaryExpression_visit(node)
        if isinstance(node.item, MethodCall) and node.item._sub is not None:
            node.item = node.item._sub

    # ✅ Method Call Expansion & Postcondition Mutation
    def MethodCall_visit(self, node):
        """
        Expands method calls and applies postcondition mutation.
        """
        super(SolidityPredicateExpansion, self).MethodCall_visit(node)
        node._sub = None
        if node.target is not None:
            targett = node.target.text()
            if targett in self.pred2post:
                tr = self.pred2post[targett]
                if node.call is not None:
                    callt = ".".join([c.text() for c in node.call])
                    if callt in tr:
                        args = [a.text() for a in node.args]
                        res = tr[callt](*args)

                        if self.preconditions:
                            pre = ""
                            if targett in self.precondition_predicates and callt in self.precondition_predicates[targett]:
                                pre = self.precondition_predicates[targett][callt](*args)
                            if targett in self.precondition_Integer_predicates and callt in self.precondition_Integer_predicates[targett]:
                                pre += " && " + self.precondition_Integer_predicates[targett][callt](*args)
                            if pre:
                                res = pre + " && " + res

                        node._sub = parse_expression(res + ";")
                        if node._sub is None:
                            self.failed = True

    # ✅ Triviality Detection
    triviality = {
        "SolArrays": {
            "grt": lambda args: args[1] == args[2] or args[1] == args[3] or args[2] == args[3],
            "lesseq": lambda args: args[1] == args[2] or args[1] == args[3] or args[2] == args[3]
        }
    }

    def is_trivial(self, mcall):
        """
        Identifies trivial method calls.
        """
        if len(mcall.call) != 1 or mcall.args is None:
            return False
        call = mcall.call[0].text()
        target = mcall.target.text()
        args = [a.text() for a in mcall.args]
        return target in self.triviality and call in self.triviality[target] and self.triviality[target][call](args)

    def is_theorypred(self, mcall):
        """
        Checks if a method call is a theory predicate.
        """
        target = mcall.target.text()
        return target in self.triviality


class SolidityExecutableSubstitution(Substitutions):
    """
    Transforms Solidity loop invariants into executable Solidity assertions,
    handling \old() expressions, offsets, quantifier expansions, and implies expressions.
    """
    errors = []

    def __init__(self, expression, root):
        super(SolidityExecutableSubstitution, self).__init__(expression, root)
        self.errors = []

    def unold(self, node):
        """Handles \old() expressions by replacing them with Solidity-compatible syntax."""
        assert isinstance(node, OldExpression)
        return parse_expression("old_" + node.args[0].text() + ";")

    def _offset(self, node, qvar):
        """Computes arithmetic offsets when handling loop variables in quantified expressions."""
        if not isinstance(node, AdditiveExpression):
            return ("", False) if node.text() == qvar else (node.text(), False)
        else:
            off1, neg1 = self._offset(node.left, qvar)
            off2, neg2 = self._offset(node.right, qvar)
            if isinstance(node, AddExpression):
                return (' + '.join([off1, off2]), neg1 or neg2)
            elif isinstance(node, SubExpression):
                return (' - '.join([off1, off2]), neg1 or neg2)

    def get_bound(self, relex, qvar):
        """Extracts loop bounds from relational expressions."""
        if isinstance(relex, GreaterExpression) or isinstance(relex, GreaterEqualExpression):
            left, right = relex.right, relex.left
        else:
            left, right = relex.left, relex.right
        strict = isinstance(relex, (GreaterExpression, LessExpression))
        qv = qvar.text()
        if right.text() == qv and left.text() != qv:
            return left, True, strict
        elif left.text() == qv and right.text() != qv:
            return right, False, strict
        self.errors.append(f"❌ Malformed bound in: {relex.text()}")
        return None, None, None

    def QuantifiedExpression_visit(self, node):
        """Transforms quantified expressions (`∀x: A ⇒ B`) into Solidity assertions."""
        node._sub = None
        if node.quantifier != node.FORALL:
            self.errors.append("❌ Existential quantification (`∃`) is not supported in Solidity.")
            return
        if len(node.variables) != 1:
            self.errors.append("❌ Cannot handle quantifications over multiple variables.")
            return

        qvar = node.variables[0].val  # Get the quantified variable
        scope = node.scope

        if not isinstance(scope, ImpliesExpression):
            self.errors.append(f"❌ Expected an `A ⇒ B` structure but got: {scope.text()}")
            return

        antecedent = scope.left  # A
        consequent = scope.right  # B

        if not isinstance(antecedent, AndExpression):
            self.errors.append(f"❌ Expected a conjunction (`A && B`) in antecedent: {antecedent.text()}")
            return

        leftmost = antecedent.left
        rightmost = antecedent.right

        if not isinstance(leftmost, RelationalExpression):
            self.errors.append(f"❌ Expected lower bound in leftmost expression: {leftmost.text()}")
            return
        if not isinstance(rightmost, RelationalExpression):
            self.errors.append(f"❌ Expected upper bound in rightmost expression: {rightmost.text()}")
            return

        lbound, llower, lstrict = self.get_bound(leftmost, qvar)
        rbound, rlower, rstrict = self.get_bound(rightmost, qvar)

        if lbound is None or rbound is None:
            self.errors.append("❌ Giving up due to malformed bound expressions.")
            return

        if llower == rlower:
            self.errors.append(f"❌ Conflicting bounds in: {antecedent.text()}")
            return

        if llower:
            low = parse_expression(lbound.text() + " + 1;") if lstrict else lbound
            high = rbound if rstrict else parse_expression(rbound.text() + " + 1;")
        else:
            low = parse_expression(rbound.text() + " + 1;") if rstrict else rbound
            high = lbound if lstrict else parse_expression(lbound.text() + " + 1;")

        if isinstance(consequent, EqualsExpression):
            pred = "QEq"
        elif isinstance(consequent, NEqualsExpression):
            pred = "QNeq"
        elif isinstance(consequent, LessExpression):
            pred = "QLess"
        elif isinstance(consequent, LessEqualExpression):
            pred = "QLessEq"
        elif isinstance(consequent, GreaterExpression):
            pred = "QGrt"
        elif isinstance(consequent, GreaterEqualExpression):
            pred = "QGrtEq"
        else:
            self.errors.append(f"❌ Cannot translate consequent: {consequent.text()}")
            return

        sub_string = f"require(({low.text()} <= {qvar}) && ({qvar} <= {high.text()}) ? ({consequent.text()}) : true, 'Quantified expression failed');"
        node._sub = parse_expression(sub_string)

    def BinaryExpression_visit(self, node):
        """Expands method calls inside binary expressions and processes quantified/implies expressions."""
        super(SolidityExecutableSubstitution, self).BinaryExpression_visit(node)

        if isinstance(node.left, (QuantifiedExpression, ImpliesExpression)):
            node.left = node.left._sub
        elif isinstance(node.left, OldExpression):
            node.left = self.unold(node.left)

        if isinstance(node.right, (QuantifiedExpression, ImpliesExpression)):
            node.right = node.right._sub
        elif isinstance(node.right, OldExpression):
            node.right = self.unold(node.right)

    def UnaryExpression_visit(self, node):
        """Expands method calls inside unary expressions and processes quantified/implies expressions."""
        super(SolidityExecutableSubstitution, self).UnaryExpression_visit(node)

        if isinstance(node.item, (QuantifiedExpression, ImpliesExpression)):
            node.item = node.item._sub
        elif isinstance(node.item, OldExpression):
            node.item = self.unold(node.item)

    def ImpliesExpression_visit(self, node):
        """
        Converts implies expressions (A ⇒ B) into Solidity ternary expressions: 
        (A ? B : true)
        """
        self.BinaryExpression_visit(node)
        node._sub = None
        try:
            node._sub = parse_expression(
                f"(({node.left.text()}) ? ({node.right.text()}) : true);"
            )
        except:
            self.errors.append("❌ Dropping malformed implies expression")


class SolidityExecutableInvariant(object):
    """
    Converts Solidity loop invariants into executable assertions.
    """
    original_node = None
    node = None
    errors = None

    def __init__(self, solidity_expression, parsed=False):
        self.errors = []
        if parsed:
            self.original_node = solidity_expression
        else:
            self.original_node = parse_expression(solidity_expression)
        self.node = self.original_node

    def get_text(self):
        return self.node.text() if self.node else ""

    def is_executable(self):
        """Checks if the Solidity invariant can be executed as a require/assert statement."""
        if self.node is None:
            return False
        try:
            return "require(" in self.node.text() or "assert(" in self.node.text()
        except:
            return False

    def make_executable(self):
        """Transforms Solidity loop invariants into Solidity assertions."""
        if self.is_executable():
            return

        transformer = SolidityExecutableSubstitution(self.node, self.node)
        self.node.accept(transformer)
        self.errors = transformer.errors

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Solidity loop invariants to executable form.")
    parser.add_argument("command", action="store", choices=["exec", "check", "quant", "dynamate"], 
                        help="convert to executable form (exec), validate (check), introduce quantifiers (quant), or apply Dynamate transformation (dynamate)")
    parser.add_argument("-e", dest="show_errors", action="store_true", help="print errors and warnings")
    parser.add_argument("--class", dest="classname", action="store", help="fully qualified class name")
    parser.add_argument("--method", dest="methodname", action="store", help="method name")
    parser.add_argument("expressions", nargs="+", metavar="E", action="append", help="Solidity expression to process")
    args = parser.parse_args()

    for expr in args.expressions[0]:
        invariant = SolidityExecutableInvariant(expr)

        if args.command == "exec":
            invariant.make_executable()
            if invariant.node:
                print(invariant.get_text())

        elif args.command == "check":
            print("✅ Valid invariant" if invariant.is_executable() else "❌ Invalid invariant")

        elif args.command == "quant":
            invariant.make_quantification()
            if invariant.node:
                print(invariant.node.text())

        elif args.command == "dynamate":
            if args.classname and args.methodname:
                method_id = args.classname + "." + args.methodname
                # 🔹 Check if method uses Integer arrays (for future Solidity optimization)
                use_integer_arrays = method_id in methods_with_Integer_arrays

                success = invariant.make_quantification(IntegerArrays=use_integer_arrays, preconditions=True)

                if invariant.node is None or not success:
                    print("❌ FAILURE:")
                else:
                    print("✅ SUCCESS:", invariant.node.text())

            else:
                print("❌ ERROR: 'dynamate' requires both --class and --method arguments")
                sys.exit(1)

        # 🔹 Improved error handling output (matches Dynamate)
        if args.show_errors:
            if len(invariant.errors) > 0:
                print("== Errors: ==")
                for err in invariant.errors:
                    print(err)
            else:
                print("== No errors ==")

