import copy
from SolidityAST import *

class ReachLocation:
    """Traverses the AST to find a specific node where analysis should start."""
    root = None
    cur_node = None
    found = False

    def __init__(self, root):
        self.root = root

    def getto_cur_node(self):
        self.root.accept(self)
        return self.cur_node

    def visit(self, node):
        if node.cur_pos:
            self.cur_node = node
            self.found = True

    def Loop_visit(self, node):
        self.visit(node)
        if hasattr(node, "condition") and node.condition:
            node.condition.accept(self)
        if hasattr(node, "body") and node.body:
            if hasattr(node, "body") and node.body:
                node.body.accept(self)



    def Expression_visit(self, node):
        self.visit(node)
        if hasattr(node, "expr") and node.expr:
            node.expr.accept(self)


    def BinaryExpression_visit(self, node):
        self.visit(node)
        if hasattr(node, "left") and node.left:
            node.left.accept(self)
        if hasattr(node, "right") and node.right:
            node.right.accept(self)


    def UnaryExpression_visit(self, node):
        self.visit(node)
        if hasattr(node, "expr") and node.expr:
            node.expr.accept(self)


    def FunctionCall_visit(self, node):
        self.visit(node)
        if node.target is not None:
            node.target.accept(self)
        for arg in node.args:
            arg.accept(self)

    def ArrayReference_visit(self, node):
        self.visit(node)
        if hasattr(node, "array") and node.array:
            node.array.accept(self)
        if hasattr(node, "index") and node.index:
            node.index.accept(self)

    def AttributeCall_visit(self, node):
        self.visit(node)
        if hasattr(node, "target") and node.target:
            node.target.accept(self)
        if hasattr(node, "attribute") and node.attribute:
            node.attribute.accept(self)


class Substitutions:
    """Base class for AST transformations and substitutions."""
    nexp = None
    root = None
    current = None

    _all_subs = None
    _p = None
    itpos = None

    def __init__(self, nexp, root):
        self.nexp = nexp
        self.root = root
        self._all_subs = []
        self._p = 0

    def __iter__(self):
        self.itpos = 0
        self.root.accept(self)
        return self

    def recopy(self):
        """
        Creates a deep copy of the AST and finds the node marked with cur_pos.
        Appends the modified tree to _all_subs only if it's unique (by .text()).
        Returns the node where substitution is to be applied.
        """
        try:
            self.current = copy.deepcopy(self.root)
        except Exception as e:
            print(f"❌ recopy(): failed to deepcopy AST root → {e}")
            return None

        # Find the substitution point
        r = ReachLocation(self.current)
        r.nexp = self.nexp  # Enable matching
        n = r.getto_cur_node()

        if not r.found or n is None:
            print("❌ recopy(): ReachLocation failed to find cur_pos node in copied AST")
            return None

        n.cur_pos = False  # Reset flag

        try:
            cur_text = self.current.text()
        except Exception as e:
            print(f"❌ recopy(): failed to call .text() on copied AST → {e}")
            return None

        # Deduplication check
        try:
            if not any(existing.text() == cur_text for existing in self._all_subs):
                self._all_subs.append(self.current)
                self._p += 1
            else:
                print(f"⚠️ Skipped duplicate substitution: {cur_text}")
        except Exception as e:
            print(f"❌ recopy(): error during deduplication check → {e}")
            return None

        return n


    def __next__(self):
        """
        Iterator: Returns the next unique substitution (if any).
        """
        while self.itpos < self._p:
            candidate = self._all_subs[self.itpos]
            self.itpos += 1
            return candidate

        raise StopIteration

    def visit(self, node):
        if node is None:
            return

        if self.nexp is None:
            if node is None:
                print("⚠️ Skipping None node in visit()")
                return

            text_fn = getattr(node, "text", None)
            if callable(text_fn):
                self._all_subs.append(node)
            else:
                print(f"⚠️ Skipping node without valid .text(): {type(node).__name__}")

            # Do not skip traversal even if node has no text
            # because its children might still be valid
        else:
            # When nexp is set, we might be substituting
            if hasattr(node, "text") and node.text() == self.nexp.text():
                r = self.recopy()
                if r is not None:
                    self._all_subs.append(r)
                    self._p += 1
                    print(f"✅ Substituted node: {node.text()} → {self.nexp.text()}")
                else:
                    print(f"⚠️ recopy() returned None for node: {type(node).__name__}")
                return  # Stop traversal for substituted match

        # 🌿 Traverse children using specialized visit methods or dynamic discovery
        method_name = f"{node.__class__.__name__}_visit"
        visitor = getattr(self, method_name, None)
        if visitor:
            visitor(node)
        else:
            for attr_name in dir(node):
                if attr_name.startswith("_") or attr_name in ("priority", "cur_pos", "accept", "text"):
                    continue
                try:
                    child = getattr(node, attr_name)
                    if isinstance(child, ASTNode):
                        self.visit(child)
                    elif isinstance(child, list):
                        for item in child:
                            if isinstance(item, ASTNode):
                                self.visit(item)
                except Exception as e:
                    print(f"⚠️ visit(): failed to access {attr_name} on {type(node).__name__} → {e}")

    def Loop_visit(self, node):
        """Handles loop constructs with substitution and safe traversal."""

        # Substitute in loop condition
        if hasattr(node, "condition") and node.condition is not None:
            try:
                if self.nexp and hasattr(node.condition, "text") and node.condition.text() == self.nexp.text():
                    r = self.recopy()
                    if r:
                        r.condition = copy.deepcopy(self.nexp)
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted loop condition: {node.condition.text()} → {self.nexp.text()}")
                else:
                    node.condition.accept(self)
            except Exception as e:
                print(f"⚠️ Loop_visit: failed to process condition → {e}")

        # Substitute inside loop body
        if hasattr(node, "body") and node.body is not None:
            try:
                node.body.accept(self)
            except Exception as e:
                print(f"⚠️ Loop_visit: failed to process body → {e}")



    def Expression_visit(self, node):
        """Handles single-expression wrappers."""
        try:
            if self.nexp and hasattr(node, "text") and node.text() == self.nexp.text():
                r = self.recopy()
                if r:
                    self._all_subs.append(r)
                    self._p += 1
                    print(f"✅ Substituted full expression node: {node.text()} → {self.nexp.text()}")
                return
        except Exception as e:
            print(f"⚠️ Expression_visit: failed substitution match → {e}")

        if hasattr(node, "expr") and node.expr is not None:
            try:
                node.expr.accept(self)
            except Exception as e:
                print(f"⚠️ Expression_visit: failed to visit inner expr → {e}")

    def BinaryExpression_visit(self, node):
        # Visit left node
        if hasattr(node, "left"):
            if node.left is None:
                print("⚠️ BinaryExpression.left is None → skipping")
            elif hasattr(node.left, "text") and self.nexp and node.left.text() == self.nexp.text():
                r = self.recopy()
                if r:
                    r.left = copy.deepcopy(self.nexp)
                    self._all_subs.append(r)
                    self._p += 1
                    print(f"✅ Substituted LEFT of BinaryExpression: {node.left.text()} → {self.nexp.text()}")
            else:
                try:
                    node.left.accept(self)
                except Exception as e:
                    print(f"⚠️ BinaryExpression_visit: error visiting left → {e}")
        else:
            print("⚠️ BinaryExpression has no 'left' attribute")

        # Visit right node
        if hasattr(node, "right"):
            if node.right is None:
                print("⚠️ BinaryExpression.right is None → skipping")
            elif hasattr(node.right, "text") and self.nexp and node.right.text() == self.nexp.text():
                r = self.recopy()
                if r:
                    r.right = copy.deepcopy(self.nexp)
                    self._all_subs.append(r)
                    self._p += 1
                    print(f"✅ Substituted RIGHT of BinaryExpression: {node.right.text()} → {self.nexp.text()}")
            else:
                try:
                    node.right.accept(self)
                except Exception as e:
                    print(f"⚠️ BinaryExpression_visit: error visiting right → {e}")
        else:
            print("⚠️ BinaryExpression has no 'right' attribute")

        

    def UnaryExpression_visit(self, node):
        if not hasattr(node, "expr"):
            print("⚠️ UnaryExpression missing 'expr' attribute → skipping")
            return

        if node.expr is None:
            print("⚠️ UnaryExpression.expr is None → skipping")
            return

        try:
            if hasattr(node.expr, "text") and self.nexp and node.expr.text() == self.nexp.text():
                r = self.recopy()
                if r:
                    r.expr = copy.deepcopy(self.nexp)
                    self._all_subs.append(r)
                    self._p += 1
                    print(f"✅ Substituted UnaryExpression.expr: {node.expr.text()} → {self.nexp.text()}")
            else:
                node.expr.accept(self)
        except Exception as e:
            print(f"⚠️ UnaryExpression_visit: error visiting expr → {e}")


    def FunctionCall_visit(self, node):
        if node.target is not None:
            try:
                if hasattr(node.target, "text") and self.nexp and node.target.text() == self.nexp.text():
                    r = self.recopy()
                    if r:
                        r.target = copy.deepcopy(self.nexp)
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted FunctionCall.target: {node.target.text()} → {self.nexp.text()}")
                else:
                    node.target.accept(self)
            except Exception as e:
                print(f"⚠️ FunctionCall_visit: error visiting target → {e}")

        for i, arg in enumerate(getattr(node, "args", [])):
            if arg is None:
                print(f"⚠️ FunctionCall_visit: args[{i}] is None, skipping")
                continue
            try:
                if hasattr(arg, "text") and self.nexp and arg.text() == self.nexp.text():
                    r = self.recopy()
                    if r:
                        r.args[i] = copy.deepcopy(self.nexp)
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted FunctionCall.args[{i}]: {arg.text()} → {self.nexp.text()}")
                else:
                    arg.accept(self)
            except Exception as e:
                print(f"⚠️ FunctionCall_visit: error visiting arg[{i}] → {e}")

    def ArrayReference_visit(self, node):
        try:
            if hasattr(node, "text") and self.nexp and node.text() == self.nexp.text():
                r = self.recopy()
                if r:
                    self._all_subs.append(r)
                    self._p += 1
                    print(f"✅ Substituted ArrayReference: {node.text()} → {self.nexp.text()}")
                return  # Stop traversal if substituted
        except Exception as e:
            print(f"⚠️ ArrayReference_visit: error checking text match → {e}")

        try:
            if hasattr(node, "array") and node.array is not None:
                node.array.accept(self)
        except Exception as e:
            print(f"⚠️ ArrayReference_visit: failed on node.array → {e}")

        try:
            if hasattr(node, "index") and node.index is not None:
                node.index.accept(self)
        except Exception as e:
            print(f"⚠️ ArrayReference_visit: failed on node.index → {e}")

    def ConditionalExpression_visit(self, node):
        if node is None:
            print("⚠️ ConditionalExpression_visit: received None node")
            return

        try:
            if hasattr(node, "text") and self.nexp and callable(node.text) and node.text() == self.nexp.text():
                r = self.recopy()
                if r:
                    self._all_subs.append(r)
                    self._p += 1
                    print(f"✅ Substituted ConditionalExpression: {node.text()} → {self.nexp.text()}")
                return  # Skip children if substitution is done
        except Exception as e:
            print(f"⚠️ ConditionalExpression_visit: failed on substitution check → {e}")

        for attr in ["condition", "then_exp", "else_exp"]:
            child = getattr(node, attr, None)
            if child:
                try:
                    child.accept(self)
                except Exception as e:
                    print(f"⚠️ ConditionalExpression_visit: failed on {attr}.accept() → {e}")

    def FeatureCall_visit(self, node):
        """Handles feature calls like object.method() or contract.call()"""
        if node is None:
            print("⚠️ FeatureCall_visit: received None node")
            return

        # Handle target
        if getattr(node, "target", None):
            try:
                if (self.nexp and hasattr(node.target, "text") and callable(node.target.text)
                        and node.target.text() == self.nexp.text()):
                    r = self.recopy()
                    if r:
                        r.target = copy.deepcopy(self.nexp)
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted FeatureCall target: {node.target.text()} → {self.nexp.text()}")
                else:
                    node.target.accept(self)
            except Exception as e:
                print(f"⚠️ FeatureCall_visit: failed on target → {e}")

        # Handle call arguments
        if getattr(node, "call", None):
            for i, c in enumerate(node.call):
                if c is None:
                    print(f"⚠️ FeatureCall_visit: call[{i}] is None → skipping")
                    continue
                try:
                    if (self.nexp and hasattr(c, "text") and callable(c.text)
                            and c.text() == self.nexp.text()):
                        r = self.recopy()
                        if r:
                            r.call[i] = copy.deepcopy(self.nexp)
                            self._all_subs.append(r)
                            self._p += 1
                            print(f"✅ Substituted FeatureCall call[{i}]: {c.text()} → {self.nexp.text()}")
                    else:
                        c.accept(self)
                except Exception as e:
                    print(f"⚠️ FeatureCall_visit: failed on call[{i}] → {e}")


    def MethodCall_visit(self, node):
        """Extends FeatureCall_visit() for function arguments"""
        if node is None:
            print("⚠️ MethodCall_visit: received None node")
            return

        self.FeatureCall_visit(node)  # Handles target and call

        if not hasattr(node, "args") or node.args is None:
            print("⚠️ MethodCall_visit: node.args is missing or None")
            return

        for i, a in enumerate(node.args):
            if a is None:
                print(f"⚠️ MethodCall_visit: node.args[{i}] is None → skipping")
                continue

            try:
                if hasattr(a, "text") and self.nexp and a.text() == self.nexp.text():
                    r = self.recopy()
                    if r is not None and r.args and i < len(r.args):
                        r.args[i] = copy.deepcopy(self.nexp)
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted MethodCall arg[{i}]: {a.text()} → {self.nexp.text()}")
                    else:
                        print(f"⚠️ MethodCall_visit: substitution failed or r.args too short")
                else:
                    a.accept(self)
            except Exception as e:
                print(f"❌ MethodCall_visit: error visiting arg[{i}] → {e}")

    def QuantifiedExpression_visit(self, node):
        """Handles quantified expressions (forall, exists, etc.)"""
        if node is None:
            print("⚠️ QuantifiedExpression_visit: received None node")
            return

        try:
            if hasattr(node, "scope") and node.scope:
                if hasattr(node.scope, "text") and self.nexp and node.scope.text() == self.nexp.text():
                    r = self.recopy()
                    if r is not None:
                        r.scope = copy.deepcopy(self.nexp)
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted QuantifiedExpression.scope: {node.scope.text()} → {self.nexp.text()}")
                node.scope.accept(self)
            else:
                print("⚠️ QuantifiedExpression_visit: node.scope is missing or None")

            if hasattr(node, "variables") and node.variables:
                for j, v in enumerate(node.variables):
                    if v is not None:
                        try:
                            v.accept(self)
                        except Exception as e:
                            print(f"❌ QuantifiedExpression_visit: failed to visit variable[{j}] → {e}")
                    else:
                        print(f"⚠️ QuantifiedExpression_visit: variable[{j}] is None → skipping")
            else:
                print("⚠️ QuantifiedExpression_visit: node.variables is missing or empty")

        except Exception as e:
            print(f"❌ QuantifiedExpression_visit: general failure → {e}")

    def AttributeCall_visit(self, node):
        """Handles Solidity attribute accesses like msg.sender or object.prop"""
        if node is None:
            print("⚠️ AttributeCall_visit: node is None → skipping")
            return

        try:
            if hasattr(node, "text") and callable(node.text):
                if self.nexp and node.text() == self.nexp.text():
                    r = self.recopy()
                    if r:
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted AttributeCall: {node.text()} → {self.nexp.text()}")
                    return
            else:
                print(f"⚠️ AttributeCall_visit: .text() missing or not callable for {type(node).__name__}")
        except Exception as e:
            print(f"❌ AttributeCall_visit: error comparing .text() → {e}")

        # Visit sub-nodes safely
        try:
            if hasattr(node, "target") and node.target is not None:
                node.target.accept(self)
        except Exception as e:
            print(f"⚠️ AttributeCall_visit: failed visiting target → {e}")

        try:
            if hasattr(node, "attribute") and node.attribute is not None:
                node.attribute.accept(self)
        except Exception as e:
            print(f"⚠️ AttributeCall_visit: failed visiting attribute → {e}")

    def Identifier_visit(self, node):
        """Handles simple identifiers like `total`, `i`, etc."""
        if node is None:
            print("⚠️ Identifier_visit: node is None → skipping")
            return

        try:
            if hasattr(node, "text") and callable(node.text):
                if self.nexp and node.text() == self.nexp.text():
                    r = self.recopy()
                    if r:
                        self._all_subs.append(r)
                        self._p += 1
                        print(f"✅ Substituted Identifier: {node.text()} → {self.nexp.text()}")
            else:
                print(f"⚠️ Identifier_visit: .text() missing or not callable for {type(node).__name__}")
        except Exception as e:
            print(f"❌ Identifier_visit: error comparing .text() → {e}")


class BooleanSubstitutions(Substitutions):
    """Handles boolean substitutions in logical expressions."""

    def __init__(self, nexp, root):
        super().__init__(nexp, root)
        self._all_subs.append(nexp)
        self._p += 1

    def ConditionalExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.condition = self.nexp
        node.cur_pos = False
        super().ConditionalExpression_visit(node)

    def EquivalenceExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.left = self.nexp
        r = self.recopy()
        r.right = self.nexp
        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def ImplicationExpression_visit(self, node):
        self.EquivalenceExpression_visit(node)

    def OrExpression_visit(self, node):
        self.EquivalenceExpression_visit(node)

    def AndExpression_visit(self, node):
        self.EquivalenceExpression_visit(node)

    def NotExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.item = self.nexp
        node.cur_pos = False
        super().UnaryExpression_visit(node)

    def MethodCall_visit(self, node):
        node.cur_pos = True
        for x in range(len(node.args)):
            r = self.recopy()
            r.args[x] = self.nexp
        node.cur_pos = False
        super().MethodCall_visit(node)

    def QuantifiedExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.scope = self.nexp
        node.cur_pos = False
        super().QuantifiedExpression_visit(node)

class ArraySubstitutions(Substitutions):
    """Handles array reference substitutions (e.g., arr[i] → arr[nexp])."""

    def ArrayReference_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.target = self.nexp.target
        r.call = self.nexp.call
        node.cur_pos = False
        super().ArrayReference_visit(node)

class CallableSubstitutions(Substitutions):
    """Handles function call substitutions where the number of arguments matches."""

    def MethodCall_visit(self, node):
        if len(node.args) == len(self.nexp.args):  # Only substitute if arg count matches
            node.cur_pos = True
            r = self.recopy()
            r.target = self.nexp.target
            r.call = self.nexp.call
            node.cur_pos = False
        super().MethodCall_visit(node)


class IntSubstitutions(Substitutions):
    """Handles integer substitutions in arithmetic and logical expressions."""

    def ConditionalExpression_visit(self, node):
        node.cur_pos = True

        # Substitute in then_exp
        r1 = self.recopy()
        r1.then_exp = self.nexp
        print(f"🔁 [CondExpr] Substituting THEN: {r1.text()}")
        self._all_subs.append(r1)
        self._p += 1

        # Substitute in else_exp
        r2 = self.recopy()
        r2.else_exp = self.nexp
        print(f"🔁 [CondExpr] Substituting ELSE: {r2.text()}")
        self._all_subs.append(r2)
        self._p += 1

        node.cur_pos = False
        super().ConditionalExpression_visit(node)

    def EqualityExpression_visit(self, node):
        node.cur_pos = True

        r1 = self.recopy()
        r1.left = self.nexp
        print(f"🔁 [EqualityExpr] Substituting LEFT: {r1.text()}")
        self._all_subs.append(r1)
        self._p += 1

        r2 = self.recopy()
        r2.right = self.nexp
        print(f"🔁 [EqualityExpr] Substituting RIGHT: {r2.text()}")
        self._all_subs.append(r2)
        self._p += 1

        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def RelationalExpression_visit(self, node):
        node.cur_pos = True

        print(f"🔁 RelationalExpression: Attempting substitution on {node}")

        r1 = self.recopy()
        r1.left = self.nexp
        print(f"✅ Substituted left: {r1.text()}")
        self._all_subs.append(r1)
        self._p += 1

        r2 = self.recopy()
        r2.right = self.nexp
        print(f"✅ Substituted right: {r2.text()}")
        self._all_subs.append(r2)
        self._p += 1

        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def AdditiveExpression_visit(self, node):
        node.cur_pos = True

        print(f"🔁 AdditiveExpression: Attempting substitution on {node}")

        r1 = self.recopy()
        r1.left = self.nexp
        print(f"✅ Substituted left: {r1.text()}")
        self._all_subs.append(r1)
        self._p += 1

        r2 = self.recopy()
        r2.right = self.nexp
        print(f"✅ Substituted right: {r2.text()}")
        self._all_subs.append(r2)
        self._p += 1

        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def MultiplicativeExpression_visit(self, node):
        node.cur_pos = True
        print(f"[🔁 Substitution] MultiplicativeExpression at: {node.text()}")

        r1 = self.recopy()
        r1.left = self.nexp
        self._all_subs.append(r1)
        self._p += 1
        print(f"[✅] Substituted left operand with: {self.nexp.text()}")

        r2 = self.recopy()
        r2.right = self.nexp
        self._all_subs.append(r2)
        self._p += 1
        print(f"[✅] Substituted right operand with: {self.nexp.text()}")

        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def PlusUnaryExpression_visit(self, node):
        node.cur_pos = True
        print(f"[🔁 Substitution] PlusUnaryExpression at: {node.text()}")

        r = self.recopy()
        r.item = self.nexp
        self._all_subs.append(r)
        self._p += 1
        print(f"[✅] Substituted unary item with: {self.nexp.text()}")

        node.cur_pos = False
        super().UnaryExpression_visit(node)

    def MinusUnaryExpression_visit(self, node):
        print(f"[↪️] Redirecting MinusUnaryExpression to PlusUnaryExpression: {node.text()}")
        self.PlusUnaryExpression_visit(node)

    def MethodCall_visit(self, node):
        node.cur_pos = True
        for x in range(len(node.args)):
            r = self.recopy()
            r.args[x] = self.nexp
            print(f"🔁 [MethodCall] Substituting arg[{x}] → {r.text()}")
            self._all_subs.append(r)
            self._p += 1
        node.cur_pos = False
        super().MethodCall_visit(node)

    def ArrayReference_visit(self, node):
        if not hasattr(node, "args") or not isinstance(node.args, list):
            print("⚠️ Skipping ArrayReference: missing or invalid `args` field.")
            return

        node.cur_pos = True
        for i in range(len(node.args)):
            print(f"🔁 Substituting into ArrayReference index {i}: replacing {node.args[i].text() if hasattr(node.args[i], 'text') else node.args[i]} with {self.nexp.text()}")
            r = self.recopy()
            r.args[i] = self.nexp
            self._all_subs.append(r)
            self._p += 1
        node.cur_pos = False

        super().ArrayReference_visit(node)


class InvariantSubstitutions(Substitutions):
    """Replaces loop conditions with inferred invariants."""
    def Loop_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.condition = self.nexp
        node.cur_pos = False
        super().Loop_visit(node)

class ExpressionSimplifier(Substitutions):
    """Simplifies arithmetic expressions in loops."""
    def Expression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        if hasattr(r, "expr"):
            r.expr = self.nexp
        node.cur_pos = False
        super().Expression_visit(node)

class ResultRemover(Substitutions):
    """Removes expressions involving result values."""
    def Expression_visit(self, node):
        super().Expression_visit(node)
        node._res = getattr(node.expr, "_res", False)
        if node._res:
            node.cur_pos = True
            r = self.recopy()
            r.expr = None  # Remove the result reference
            node.cur_pos = False

class AgingSubstitutions(Substitutions):
    """Handles numeric aging by adding a fixed value (e.g., +1 or -1) to expressions."""

    def add_combine(self, old, new):
        res = SolidityAST.AddExpression()  # Assuming SolidityAST has an AddExpression class
        res.left = old
        res.right = new
        return res

    def ConditionalExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.then_exp = self.add_combine(r.then_exp, self.nexp)
        r = self.recopy()
        r.else_exp = self.add_combine(r.else_exp, self.nexp)
        node.cur_pos = False
        super().ConditionalExpression_visit(node)

    def EqualityExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.left = self.add_combine(r.left, self.nexp)
        r = self.recopy()
        r.right = self.add_combine(r.right, self.nexp)
        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def RelationalExpression_visit(self, node):
        self.EqualityExpression_visit(node)

    def AdditiveExpression_visit(self, node):
        self.EqualityExpression_visit(node)

    def MultiplicativeExpression_visit(self, node):
        self.EqualityExpression_visit(node)

    def PlusUnaryExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.item = self.add_combine(r.item, self.nexp)
        node.cur_pos = False
        super().UnaryExpression_visit(node)

    def MinusUnaryExpression_visit(self, node):
        self.PlusUnaryExpression_visit(node)

    def MethodCall_visit(self, node):
        node.cur_pos = True
        for x in range(len(node.args)):
            r = self.recopy()
            r.args[x] = self.add_combine(r.args[x], self.nexp)
        node.cur_pos = False
        super().MethodCall_visit(node)

    def ArrayReference_visit(self, node):
        self.MethodCall_visit(node)

class WeakeningSubstitutions(Substitutions):
    """Handles boolean substitutions by weakening constraints."""

    def __init__(self, nexp, root):
        super().__init__(nexp, root)
        # The first mutation weakens the whole root expression
        self._all_subs.append(self.impl_combine(nexp, root))
        self._p += 1

    def impl_combine(self, ant, cons):
        res = SolidityAST.ImpliesExpression()  # Assuming SolidityAST has an ImpliesExpression class
        res.left = ant
        res.right = cons
        return res

    def or_combine(self, left, right):
        res = SolidityAST.OrExpression()  # Assuming SolidityAST has an OrExpression class
        res.left = left
        res.right = right
        return res

    def ConditionalExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.condition = self.or_combine(r.condition, self.nexp)
        node.cur_pos = False
        super().ConditionalExpression_visit(node)

    def EquivalenceExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        r.left = self.impl_combine(self.nexp, r.left)
        r = self.recopy()
        r.right = self.impl_combine(self.nexp, r.right)
        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def ImplicationExpression_visit(self, node):
        self.EquivalenceExpression_visit(node)

    def OrExpression_visit(self, node):
        """Handles OR (||) expressions by weakening them."""
        self.EquivalenceExpression_visit(node)

    def AndExpression_visit(self, node):
        """Handles AND (&&) expressions by weakening them."""
        self.EquivalenceExpression_visit(node)

    def NotExpression_visit(self, node):
        """Weakens NOT (!) expressions using implication."""
        node.cur_pos = True
        r = self.recopy()
        r.item = self.impl_combine(self.nexp, r.item)
        node.cur_pos = False
        super().UnaryExpression_visit(node)

    def MethodCall_visit(self, node):
        """Weakens function call arguments."""
        node.cur_pos = True
        for x in range(len(node.args)):
            r = self.recopy()
            r.args[x] = self.impl_combine(self.nexp, r.args[x])
        node.cur_pos = False
        super().MethodCall_visit(node)

    def QuantifiedExpression_visit(self, node):
        """Weakens quantified expressions (forall, exists)."""
        node.cur_pos = True
        r = self.recopy()
        r.scope = self.impl_combine(self.nexp, r.scope)
        node.cur_pos = False
        super().QuantifiedExpression_visit(node)

class PredicateExtractor(Substitutions):
    """Extracts all atomic boolean expressions from the AST."""

    def __init__(self, root):
        super().__init__(None, root)
        self._results = []

        if root is None:
            print("❌ PredicateExtractor error: root is None (invalid AST input)")
            return

        try:
            print(f"\n🔍 Visiting AST root: {type(root).__name__}")
            if hasattr(root, "text") and callable(root.text):
                print(f"   └ root.text(): {root.text()}")
            else:
                print("   └ root.text(): <not callable or missing>")

            if hasattr(root, "left") or hasattr(root, "right"):
                print(f"   └ left: {getattr(root, 'left', '<none>')}")
                print(f"   └ right: {getattr(root, 'right', '<none>')}")

            print("\n📦 Full AST dump before PredicateExtractor:")
            dump_ast(root)

            # Traverse AST
            self.visit(root)

            # Collect valid sub-nodes
            self._results = []
            for i, node in enumerate(self._all_subs):
                if node is None:
                    print(f"⚠️ _all_subs[{i}] is None → skipping")
                    continue

                if not hasattr(node, "text"):
                    print(f"⚠️ _all_subs[{i}] is of type {type(node).__name__} without `.text()`")
                    dump_ast(node)
                    continue

                text_fn = getattr(node, "text", None)
                if not callable(text_fn):
                    print(f"⚠️ _all_subs[{i}].text is not callable (type: {type(text_fn)})")
                    dump_ast(node)
                    continue

                self._results.append(node)

        except Exception as e:
            print(f"⚠️ PredicateExtractor failed for root '{type(root).__name__}' → {e}")
            self._results = []

    def __iter__(self):
        return iter(self._results)

    def __len__(self):
        return len(self._results)

    def __getitem__(self, idx):
        return self._results[idx]

    def MethodCall_visit(self, node):
        """If a method has arguments, consider it a predicate and extract it."""
        if node and hasattr(node, "args") and len(node.args) > 0:
            self._all_subs.append(node)
            self._p += 1

    def OldExpression_visit(self, node):
        """Skip \old expressions; treat as method call but don't add."""
        pass  # Explicitly ignore


class ResultRemover(Substitutions):
    """Removes expressions involving `\result` in JML contracts."""

    def __init__(self, root):
        super().__init__(None, root)

    def ConditionalExpression_visit(self, node):
        super().ConditionalExpression_visit(node)
        node._res = any(getattr(x, "_res", False) for x in [node.condition, node.then_exp, node.else_exp])


    def BinaryExpression_visit(self, node):
        super().BinaryExpression_visit(node)
        node._res = node.left._res or node.right._res
        node.cur_pos = True
        if node.left._res:
            r = self.recopy()
            r.left = copy.deepcopy(r.right)
            r = self.recopy()
            ne = SolidityAST.NotExpression()
            ne.item = copy.deepcopy(r.right)
            r.left = ne
        if node.right._res:
            node.cur_pos = True
            r = self.recopy()
            r.right = copy.deepcopy(r.left)
            r = self.recopy()
            ne = SolidityAST.NotExpression()
            ne.item = copy.deepcopy(r.left)
            r.right = ne
        node.cur_pos = False

    def UnaryExpression_visit(self, node):
        super().UnaryExpression_visit(node)
        node._res = node.item._res

    def FeatureCall_visit(self, node):
        super().FeatureCall_visit(node)
        if node.target is not None:
            node._res = node.target._res
        if node.call is not None:
            for c in node.call:
                if c:
                    node._res = node._res or getattr(c, "_res", False)

        
    def ResultExpression_visit(self, node):
        """Mark this node as containing a `\result` expression."""
        node._res = True


class OldAdder(Substitutions):
    """Adds `\old` expressions to operands of binary and unary expressions."""

    def BinaryExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        oe = SolidityAST.OldExpression()
        oe.args = [r.left]
        r.left = oe
        r = self.recopy()
        oe = SolidityAST.OldExpression()
        oe.args = [r.right]
        r.right = oe
        node.cur_pos = False
        super().BinaryExpression_visit(node)

    def UnaryExpression_visit(self, node):
        node.cur_pos = True
        r = self.recopy()
        oe = SolidityAST.OldExpression()
        oe.args = [r.item]
        r.item = oe
        node.cur_pos = False
        super().UnaryExpression_visit(node)


def dump_ast(node, indent=0):
    prefix = " " * indent
    if node is None:
        print(f"{prefix}⚠️ None node")
        return

    node_type = type(node).__name__
    text_func = getattr(node, "text", None)
    text_val = text_func() if callable(text_func) else "<no .text()>"

    print(f"{prefix}🔸 {node_type}: {text_val}")

    # Recursively print known child attributes (expand this as needed)
    for attr in ["left", "right", "expr", "condition", "then_exp", "else_exp", 
                 "target", "array", "index", "scope", "body", "attribute"]:
        child = getattr(node, attr, None)
        if child is not None:
            print(f"{prefix} ├── {attr}:")
            dump_ast(child, indent + 4)
        else:
            if hasattr(node, attr):
                print(f"{prefix} ├── {attr}: ⚠️ None")

    # Handle lists (e.g., args, variables, call)
    for list_attr in ["args", "variables", "call"]:
        children = getattr(node, list_attr, [])
        if children:
            print(f"{prefix} ├── {list_attr}:")
            for i, c in enumerate(children):
                if c is None:
                    print(f"{prefix} │   [{i}] ⚠️ None")
                else:
                    dump_ast(c, indent + 6)

    # Recurse into any children not covered above
    # Optionally: use dir(node) to introspect unknown attributes
