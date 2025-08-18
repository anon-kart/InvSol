import inspect

class ASTNode(object):
    cur_pos = False
    _res = False
    priority = 1000

    def text(self):
        return str(self.__class__.__name__)

    def par(self, s):
        return "(" + s + ")"

    def accept(self, visitor):
        found = False
        cn = self.__class__
        for c in [x.__name__ for x in inspect.getmro(cn)]:
            if c != "object" and hasattr(visitor, c + "_visit"):
                getattr(visitor, c + "_visit")(self)
                found = True
                break
        if not found:
            visitor.visit(self)

    def __eq__(self, other):
        try:
            return self.text() == other.text()
        except Exception:
            return False

    def __hash__(self):
        try:
            return hash(self.text())
        except Exception:
            return super().__hash__()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.text()})"


class Expression(ASTNode):
    pass


class Literal(Expression):
    def __init__(self, val=None):
        self.val = val

    def text(self):
        return str(self.val)


class IntLiteral(Literal):
    pass


class BoolLiteral(Literal):
    def text(self):
        return "true" if self.val else "false"


class StringLiteral(Literal):
    def text(self):
        return f'"{self.val}"'


class Identifier(Expression):
    def __init__(self, val=""):
        self.val = val

    def text(self):
        return self.val


class ConditionalExpression(Expression):
    priority = 10

    def __init__(self, condition=None, then_exp=None, else_exp=None):
        self.condition = condition
        self.then_exp = then_exp
        self.else_exp = else_exp

    def text(self):
        return self.par(f"{self.condition.text()} ? {self.then_exp.text()} : {self.else_exp.text()}")


class BinaryExpression(Expression):
    priority = 20
    associative = False

    def __init__(self, op=None, left=None, right=None):
        self.left = left
        self.right = right
        self.op = op

    def text(self):
        if self.left is None and self.right is None:
            return f"<empty {self.op}>"
        elif self.left is None:
            rt = self.right.text() if hasattr(self.right, 'text') else str(self.right)
            return f"<missing> {self.op} {rt}"
        elif self.right is None:
            lt = self.left.text() if hasattr(self.left, 'text') else str(self.left)
            return f"{lt} {self.op} <missing>"

        lt = self.left.text() if self.left.priority > self.priority or \
            (self.left.priority == self.priority and self.associative) else self.par(self.left.text())

        rt = self.right.text() if self.right.priority > self.priority or \
            (self.right.priority == self.priority and self.associative) else self.par(self.right.text())

        return lt + " " + self.op + " " + rt

    def aggregate(self, ls):
        if not ls:
            self.left = None
            self.right = None
            return

        if isinstance(ls[0], tuple):
            # List of (left, op, right) tuples
            if len(ls) == 1:
                self.left, self.op, self.right = ls[0]
            else:
                self.left, self.op, right_expr = ls[0]
                right_node = BinaryExpression()
                right_node.aggregate(ls[1:])
                self.right = right_node
        else:
            # List of simple operands for a repeated operator
            if len(ls) == 1:
                self.left = ls[0]
                self.right = None
            elif len(ls) == 2:
                self.left = ls[0]
                self.right = ls[1]
            else:
                self.left = ls[0]
                right_node = BinaryExpression(self.op)
                right_node.aggregate(ls[1:])
                self.right = right_node


class IffExpression(BinaryExpression):
    def __init__(self, left=None, right=None):
        super().__init__("<==>", left, right)


class NIffExpression(BinaryExpression):
    def __init__(self, left=None, right=None):
        super().__init__("<=!=>", left, right)


class ImpliesExpression(BinaryExpression):
    def __init__(self, left=None, right=None):
        super().__init__("==>", left, right)


class AndExpression(BinaryExpression):
    def __init__(self, left=None, right=None):
        super().__init__("&&", left, right)
        self.associative = True
        self.priority = 70


class OrExpression(BinaryExpression):
    def __init__(self, left=None, right=None):
        super().__init__("||", left, right)
        self.associative = True
        self.priority = 60


class NotExpression(Expression):
    priority = 220

    def __init__(self):
        self.item = None
        self.op = "!"

    def text(self):
        t = self.item.text() if self.item.priority > self.priority else self.par(self.item.text())
        return self.op + t


class MinusUnaryExpression(Expression):
    priority = 220

    def __init__(self):
        self.item = None
        self.op = "-"

    def text(self):
        t = self.item.text() if self.item.priority > self.priority else self.par(self.item.text())
        return self.op + t


class BitwiseNotExpression(Expression):
    priority = 220

    def __init__(self):
        self.item = None
        self.op = "~"

    def text(self):
        t = self.item.text() if self.item.priority > self.priority else self.par(self.item.text())
        return self.op + t


class ResultExpression(Identifier):
    def __init__(self):
        super().__init__("\\result")


class OldExpression(Expression):
    def __init__(self):
        self.item = None

    def text(self):
        return f"\\old({self.item.text()})"


class ForallExpression(Expression):
    def __init__(self):
        self.var = ""
        self.typ = None
        self.cond = None

    def text(self):
        return f"\\forall {self.var}:{self.typ.text()}; {self.cond.text()}"


class ExistsExpression(Expression):
    def __init__(self):
        self.var = ""
        self.typ = None
        self.cond = None

    def text(self):
        return f"\\exists {self.var}:{self.typ.text()}; {self.cond.text()}"


class TypeLiteral(Expression):
    def __init__(self, typename):
        self.typename = typename

    def text(self):
        return self.typename


class AttributeCall(Expression):
    def __init__(self):
        self.target = None
        self.call = []

    def text(self):
        parts = [self.target.text()] if self.target else []
        parts += [x.text() for x in self.call]
        return ".".join(parts)


class MethodCall(AttributeCall):
    def __init__(self):
        super().__init__()
        self.args = []

    def text(self):
        def stringify(arg):
            if hasattr(arg, 'text') and callable(arg.text):
                return arg.text()
            elif hasattr(arg, 'getText') and callable(arg.getText):
                return arg.getText()
            else:
                return str(arg)

        args_text = ", ".join(stringify(arg) for arg in self.args)
        return super().text() + "(" + args_text + ")"


class ArrayReference(Expression):
    def __init__(self):
        self.target = None  # should be Identifier or another expression
        self.args = []      # list of one or more expressions

    def text(self):
        target_text = self.target.text() if self.target else "<missing>"
        args_text = ", ".join(arg.text() for arg in self.args)
        return f"{target_text}[{args_text}]"

# === Utility functions for ginpink.py ===

def make_binop(op, left, right):
    node = BinaryExpression(op)
    node.left = left
    node.right = right
    return node

def make_unop(op, expr):
    if op == "!":
        node = NotExpression()
    elif op == "-":
        node = MinusUnaryExpression()
    else:
        raise ValueError(f"Unsupported unary operator: {op}")
    node.item = expr
    return node

def make_implies(left, right):
    node = ImpliesExpression()
    node.left = left
    node.right = right
    return node

def convert_parser_expr(expr):
    """
    Converts ANTLR parser expressions into internal AST node representations.
    """
    if hasattr(expr, 'getText'):
        txt = expr.getText().strip()

        if '>=' in txt:
            left, right = txt.split(">=")
            return BinaryExpression(op=">=", left=Identifier(left.strip()), right=Identifier(right.strip()))
        elif '<=' in txt:
            left, right = txt.split("<=")
            return BinaryExpression(op="<=", left=Identifier(left.strip()), right=Identifier(right.strip()))
        elif '==' in txt:
            left, right = txt.split("==")
            return BinaryExpression(op="==", left=Identifier(left.strip()), right=Identifier(right.strip()))
        elif '!=' in txt:
            left, right = txt.split("!=")
            return BinaryExpression(op="!=", left=Identifier(left.strip()), right=Identifier(right.strip()))
        elif txt.isnumeric():
            return IntLiteral(val=int(txt))
        else:
            return Identifier(val=txt)

    return expr  # Fallback

