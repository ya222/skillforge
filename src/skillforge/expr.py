"""A deliberately tiny expression language for `when` conditions on blocks.

Grammar (the whole thing)::

    expr    := or_expr
    or_expr := and_expr ("or" and_expr)*
    and_expr:= not_expr ("and" not_expr)*
    not_expr:= "not" not_expr | cmp
    cmp     := primary (("==" | "!=" | "in") primary)?
    primary := "(" expr ")" | literal | path
    path    := "params" ("." NAME)+
    literal := STRING | INT | "true" | "false"

There is no arithmetic, no function calls, no indexing and no attribute access
outside ``params``. Expressions are parsed, never ``eval``'d.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from skillforge.errors import ExprError

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<string>"[^"]*"|'[^']*')
  | (?P<int>\d+)
  | (?P<op>==|!=)
  | (?P<punct>[()])
  | (?P<name>[A-Za-z_][A-Za-z0-9_.]*)
    """,
    re.VERBOSE,
)

_KEYWORDS = {"and", "or", "not", "in", "true", "false"}


@dataclass(frozen=True)
class _Token:
    kind: str
    value: Any
    pos: int


def _tokenize(source: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    while pos < len(source):
        match = _TOKEN_RE.match(source, pos)
        if match is None:
            raise ExprError(f"unexpected character {source[pos]!r} at position {pos} in {source!r}")
        pos = match.end()
        kind = match.lastgroup
        text = match.group()
        if kind == "ws":
            continue
        if kind == "string":
            tokens.append(_Token("literal", text[1:-1], match.start()))
        elif kind == "int":
            tokens.append(_Token("literal", int(text), match.start()))
        elif kind == "name":
            if text in ("true", "false"):
                tokens.append(_Token("literal", text == "true", match.start()))
            elif text in _KEYWORDS:
                tokens.append(_Token(text, text, match.start()))
            else:
                tokens.append(_Token("path", text, match.start()))
        else:
            tokens.append(_Token(text, text, match.start()))
    tokens.append(_Token("end", None, len(source)))
    return tokens


class _Parser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.tokens = _tokenize(source)
        self.index = 0

    @property
    def current(self) -> _Token:
        return self.tokens[self.index]

    def take(self, kind: str) -> _Token:
        token = self.current
        if token.kind != kind:
            raise ExprError(
                f"expected {kind} but found {token.value!r} at position {token.pos} "
                f"in {self.source!r}"
            )
        self.index += 1
        return token

    def accept(self, kind: str) -> bool:
        if self.current.kind == kind:
            self.index += 1
            return True
        return False

    def parse(self, params: dict[str, Any]) -> Any:
        value = self.parse_or(params)
        self.take("end")
        return value

    def parse_or(self, params: dict[str, Any]) -> Any:
        value = self.parse_and(params)
        while self.accept("or"):
            right = self.parse_and(params)
            value = bool(value) or bool(right)
        return value

    def parse_and(self, params: dict[str, Any]) -> Any:
        value = self.parse_not(params)
        while self.accept("and"):
            right = self.parse_not(params)
            value = bool(value) and bool(right)
        return value

    def parse_not(self, params: dict[str, Any]) -> Any:
        if self.accept("not"):
            return not bool(self.parse_not(params))
        return self.parse_cmp(params)

    def parse_cmp(self, params: dict[str, Any]) -> Any:
        left = self.parse_primary(params)
        for kind in ("==", "!=", "in"):
            if self.accept(kind):
                right = self.parse_primary(params)
                if kind == "==":
                    return left == right
                if kind == "!=":
                    return left != right
                if not isinstance(right, (list, str, dict)):
                    raise ExprError(
                        f"`in` needs a list or string on the right, got {type(right).__name__} "
                        f"in {self.source!r}"
                    )
                return left in right
        return left

    def parse_primary(self, params: dict[str, Any]) -> Any:
        if self.accept("("):
            value = self.parse_or(params)
            self.take(")")
            return value
        token = self.current
        if token.kind == "literal":
            self.index += 1
            return token.value
        if token.kind == "path":
            self.index += 1
            return _lookup(token.value, params, self.source)
        raise ExprError(f"unexpected {token.value!r} at position {token.pos} in {self.source!r}")


def _lookup(path: str, params: dict[str, Any], source: str) -> Any:
    parts = path.split(".")
    if parts[0] != "params" or len(parts) != 2:
        raise ExprError(
            f"`{path}` is not addressable in {source!r}; only `params.<name>` is allowed"
        )
    name = parts[1]
    if name not in params:
        raise ExprError(f"`params.{name}` is not declared by this skill (used in {source!r})")
    return params[name]


def evaluate(source: str, params: dict[str, Any]) -> bool:
    """Evaluate a `when` expression against resolved params."""
    return bool(_Parser(source).parse(params))


def references(source: str) -> set[str]:
    """Every `params.<name>` an expression mentions, without evaluating it."""
    names: set[str] = set()
    for token in _tokenize(source):
        if token.kind == "path":
            parts = str(token.value).split(".")
            if parts[0] != "params" or len(parts) != 2:
                raise ExprError(
                    f"`{token.value}` is not addressable in {source!r}; "
                    "only `params.<name>` is allowed"
                )
            names.add(parts[1])
    return names
