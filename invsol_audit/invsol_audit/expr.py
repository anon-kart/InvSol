from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

TOKEN_RE = re.compile(
    r"""
    \s*(?:
      (?P<num>\d+)
    | (?P<name>[A-Za-z_]\w*)
    | (?P<op>==|!=|<=|>=|=>|&&|\|\||[-+*/%<>()\[\].,])
    )
    """,
    re.VERBOSE,
)

COMPARISONS = {"==", "!=", "<", "<=", ">", ">="}
ARITHMETIC = {"+", "-", "*", "/", "%"}
LOGICAL = {"&&", "||", "=>"}

ABSTRACT_CALLS = {"sum", "old", "entry", "count", "max", "min"}


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class Num:
    value: int


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Call:
    name: str
    args: Tuple[Any, ...]


@dataclass(frozen=True)
class Index:
    base: Any
    key: Any


@dataclass(frozen=True)
class Member:
    base: Any
    field: str


@dataclass(frozen=True)
class Binary:
    op: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Not:
    operand: Any


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    position = 0
    length = len(text)
    while position < length:
        match = TOKEN_RE.match(text, position)
        if not match or match.end() == position:
            remainder = text[position:].strip()
            if not remainder:
                break
            raise ParseError(f"cannot tokenise at {remainder!r}")
        position = match.end()
        token = match.group("num") or match.group("name") or match.group("op")
        if token is not None:
            tokens.append(token)
    return tokens


class Parser:
    """
    Recursive descent over the small expression language the inference stage
    emits: arithmetic, comparisons, implication, indexing, member access, and a
    handful of abstract calls such as sum and old.
    """

    def __init__(self, tokens: List[str]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self) -> str:
        token = self.peek()
        if token is None:
            raise ParseError("unexpected end of expression")
        self.pos += 1
        return token

    def expect(self, token: str) -> None:
        actual = self.take()
        if actual != token:
            raise ParseError(f"expected {token!r} but found {actual!r}")

    def parse(self) -> Any:
        node = self.parse_implication()
        if self.peek() is not None:
            raise ParseError(f"trailing input at {self.peek()!r}")
        return node

    def parse_implication(self) -> Any:
        left = self.parse_or()
        if self.peek() == "=>":
            self.take()
            return Binary("=>", left, self.parse_implication())
        return left

    def parse_or(self) -> Any:
        node = self.parse_and()
        while self.peek() == "||":
            self.take()
            node = Binary("||", node, self.parse_and())
        return node

    def parse_and(self) -> Any:
        node = self.parse_comparison()
        while self.peek() == "&&":
            self.take()
            node = Binary("&&", node, self.parse_comparison())
        return node

    def parse_comparison(self) -> Any:
        node = self.parse_additive()
        if self.peek() in COMPARISONS:
            op = self.take()
            return Binary(op, node, self.parse_additive())
        return node

    def parse_additive(self) -> Any:
        node = self.parse_multiplicative()
        while self.peek() in {"+", "-"}:
            op = self.take()
            node = Binary(op, node, self.parse_multiplicative())
        return node

    def parse_multiplicative(self) -> Any:
        node = self.parse_unary()
        while self.peek() in {"*", "/", "%"}:
            op = self.take()
            node = Binary(op, node, self.parse_unary())
        return node

    def parse_unary(self) -> Any:
        token = self.peek()
        if token == "-":
            self.take()
            return Binary("-", Num(0), self.parse_unary())
        if token == "!":
            self.take()
            return Not(self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self) -> Any:
        node = self.parse_atom()
        while True:
            token = self.peek()
            if token == "[":
                self.take()
                key = self.parse_implication()
                self.expect("]")
                node = Index(node, key)
            elif token == ".":
                self.take()
                node = Member(node, self.take())
            else:
                return node

    def parse_atom(self) -> Any:
        token = self.take()

        if token == "(":
            node = self.parse_implication()
            self.expect(")")
            return node

        if token.isdigit():
            return Num(int(token))

        if not re.match(r"^[A-Za-z_]\w*$", token):
            raise ParseError(f"unexpected token {token!r}")

        if self.peek() == "(":
            self.take()
            args: List[Any] = []
            if self.peek() != ")":
                args.append(self.parse_implication())
                while self.peek() == ",":
                    self.take()
                    args.append(self.parse_implication())
            self.expect(")")
            return Call(token, tuple(args))

        return Var(token)


def parse_expression(text: str) -> Any:
    return Parser(tokenize(text)).parse()


def is_boolean(node: Any) -> bool:
    if isinstance(node, Binary):
        return node.op in COMPARISONS or node.op in LOGICAL
    return isinstance(node, Not)


def free_variables(node: Any) -> Set[str]:
    """
    Names the expression depends on, with abstract calls folded into a single
    symbol so that sum(balances) is one unknown rather than a function of one.
    """
    found: Set[str] = set()

    def walk(item: Any) -> None:
        if isinstance(item, Var):
            found.add(item.name)
        elif isinstance(item, Num):
            return
        elif isinstance(item, Call):
            found.add(symbol_for(item))
        elif isinstance(item, Member):
            found.add(symbol_for(item))
        elif isinstance(item, Index):
            found.add(symbol_for(item))
        elif isinstance(item, Binary):
            walk(item.left)
            walk(item.right)
        elif isinstance(item, Not):
            walk(item.operand)

    walk(node)
    return found


OPERATOR_WORDS = {
    "+": "plus",
    "-": "minus",
    "*": "times",
    "/": "div",
    "%": "mod",
    "**": "pow",
}


def symbol_for(node: Any) -> str:
    """
    A stable symbol name for a term treated as an opaque value.

    Arrays, mappings and aggregate calls are abstracted rather than modelled
    element by element, which keeps the encoding inside a decidable fragment.
    """
    if isinstance(node, Var):
        return node.name
    if isinstance(node, Num):
        return str(node.value)
    if isinstance(node, Member):
        return f"{symbol_for(node.base)}_{node.field}"
    if isinstance(node, Index):
        return f"{symbol_for(node.base)}_at_{symbol_for(node.key)}"
    if isinstance(node, Call):
        inner = "_".join(symbol_for(a) for a in node.args)
        return f"{node.name}_{inner}" if inner else node.name
    if isinstance(node, Binary):
        # An index can be computed, as in buffer[(head + i) % CAPACITY]. The
        # element is opaque either way, so the whole subscript becomes part of
        # the name rather than a reason to give up on the loop.
        word = OPERATOR_WORDS.get(node.op)
        if word:
            return f"{symbol_for(node.left)}_{word}_{symbol_for(node.right)}"
    if isinstance(node, Not):
        return f"not_{symbol_for(node.operand)}"
    raise ParseError(f"cannot name {node!r}")


def rename(node: Any, mapping: Dict[str, str]) -> Any:
    """
    Substitute variable names, used to build the post-state copy of a relation.
    """
    if isinstance(node, Var):
        return Var(mapping.get(node.name, node.name))
    if isinstance(node, Num):
        return node
    if isinstance(node, Call):
        return Call(node.name, tuple(rename(a, mapping) for a in node.args))
    if isinstance(node, Member):
        return Member(rename(node.base, mapping), node.field)
    if isinstance(node, Index):
        return Index(rename(node.base, mapping), rename(node.key, mapping))
    if isinstance(node, Binary):
        return Binary(node.op, rename(node.left, mapping), rename(node.right, mapping))
    if isinstance(node, Not):
        return Not(rename(node.operand, mapping))
    return node


def render(node: Any) -> str:
    if isinstance(node, Var):
        return node.name
    if isinstance(node, Num):
        return str(node.value)
    if isinstance(node, Call):
        return f"{node.name}({', '.join(render(a) for a in node.args)})"
    if isinstance(node, Member):
        return f"{render(node.base)}.{node.field}"
    if isinstance(node, Index):
        return f"{render(node.base)}[{render(node.key)}]"
    if isinstance(node, Binary):
        return f"({render(node.left)} {node.op} {render(node.right)})"
    if isinstance(node, Not):
        return f"!({render(node.operand)})"
    return str(node)
