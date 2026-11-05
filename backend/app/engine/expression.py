"""Safe OSCAR expression tokenizer, parser, validator, and interpreter.

The module deliberately implements a small recursive-descent language. User
text is never handed to Python, a database, or another general-purpose runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

from app.engine.input_validation import finite_number

MAX_EXPRESSION_LENGTH = 2_000
MAX_AST_DEPTH = 20
MAX_AST_NODES = 200
MAX_CASE_BRANCHES = 20
MAX_LIST_ITEMS = 50

type ExpressionType = Literal["NUMBER", "STRING", "BOOLEAN", "NULL", "UNKNOWN"]
type Scalar = int | float | str | bool | None


class ExpressionError(ValueError):
    """Base safe error carrying source position without payload values."""

    def __init__(self, message: str, *, line: int = 1, col: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col


class ExpressionParseError(ExpressionError):
    pass


class ExpressionValidationError(ExpressionError):
    pass


class ExpressionEvaluationError(ExpressionError):
    pass


@dataclass(frozen=True, slots=True)
class LiteralNode:
    kind: Literal["literal"]
    value: Scalar


@dataclass(frozen=True, slots=True)
class IdentifierNode:
    kind: Literal["identifier"]
    path: str


@dataclass(frozen=True, slots=True)
class UnaryNode:
    kind: Literal["unary"]
    operator: Literal["NOT", "-"]
    operand: ExprNode


@dataclass(frozen=True, slots=True)
class BinaryNode:
    kind: Literal["binary"]
    operator: Literal["OR", "AND", "=", "!=", ">", ">=", "<", "<=", "+", "-", "*", "/"]
    left: ExprNode
    right: ExprNode


@dataclass(frozen=True, slots=True)
class IsNullNode:
    kind: Literal["is_null"]
    operand: ExprNode
    negated: bool


@dataclass(frozen=True, slots=True)
class InNode:
    kind: Literal["in"]
    operand: ExprNode
    values: tuple[LiteralNode, ...]
    negated: bool


@dataclass(frozen=True, slots=True)
class FunctionNode:
    kind: Literal["function"]
    name: Literal["MIN", "MAX", "ROUND", "ABS", "COALESCE"]
    arguments: tuple[ExprNode, ...]


@dataclass(frozen=True, slots=True)
class CaseBranch:
    when: ExprNode
    then: ExprNode


@dataclass(frozen=True, slots=True)
class CaseNode:
    kind: Literal["case"]
    branches: tuple[CaseBranch, ...]
    default: ExprNode | None


type ExprNode = (
    LiteralNode
    | IdentifierNode
    | UnaryNode
    | BinaryNode
    | IsNullNode
    | InNode
    | FunctionNode
    | CaseNode
)


@dataclass(frozen=True, slots=True)
class ParsedExpression:
    root: ExprNode
    referenced_features: tuple[str, ...]
    normalized_preview: str
    node_count: int


@dataclass(frozen=True, slots=True)
class ValidatedExpression:
    root: ExprNode
    referenced_features: tuple[str, ...]
    normalized_preview: str
    node_count: int
    inferred_type: ExpressionType


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    value: str
    line: int
    col: int


_KEYWORDS = {
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "OR",
    "AND",
    "NOT",
    "IN",
    "IS",
    "NULL",
    "TRUE",
    "FALSE",
}
_FUNCTIONS = {"MIN", "MAX", "ROUND", "ABS", "COALESCE"}
_COMPARISONS = {"=", "!=", ">", ">=", "<", "<="}


def _is_ascii_letter(value: str) -> bool:
    return "a" <= value <= "z" or "A" <= value <= "Z" or value == "_"


def _is_ascii_alnum(value: str) -> bool:
    return _is_ascii_letter(value) or "0" <= value <= "9"


def _tokenize(text: str) -> list[_Token]:
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ExpressionParseError(f"expression exceeds {MAX_EXPRESSION_LENGTH} characters")
    tokens: list[_Token] = []
    index = 0
    line = 1
    col = 1
    while index < len(text):
        char = text[index]
        if char == "\x00":
            raise ExpressionParseError("NUL bytes are not allowed", line=line, col=col)
        if char.isspace():
            if char == "\n":
                line += 1
                col = 1
            else:
                col += 1
            index += 1
            continue
        start_line, start_col = line, col
        if char == "'":
            index += 1
            col += 1
            string_parts: list[str] = []
            closed = False
            while index < len(text):
                current = text[index]
                if current == "\\":
                    raise ExpressionParseError(
                        "backslash escapes are not supported", line=line, col=col
                    )
                if current == "'":
                    if index + 1 < len(text) and text[index + 1] == "'":
                        string_parts.append("'")
                        index += 2
                        col += 2
                        continue
                    index += 1
                    col += 1
                    closed = True
                    break
                if current == "\n":
                    raise ExpressionParseError(
                        "string literals cannot span lines", line=line, col=col
                    )
                string_parts.append(current)
                index += 1
                col += 1
            if not closed:
                raise ExpressionParseError(
                    "unterminated string literal", line=start_line, col=start_col
                )
            tokens.append(_Token("STRING", "".join(string_parts), start_line, start_col))
            continue
        if "0" <= char <= "9":
            begin = index
            seen_dot = False
            while index < len(text):
                current = text[index]
                if "0" <= current <= "9":
                    index += 1
                    col += 1
                elif current == "." and not seen_dot:
                    seen_dot = True
                    index += 1
                    col += 1
                else:
                    break
            number_text = text[begin:index]
            if number_text.endswith("."):
                raise ExpressionParseError("invalid number literal", line=start_line, col=start_col)
            tokens.append(_Token("NUMBER", number_text, start_line, start_col))
            continue
        if _is_ascii_letter(char):
            begin = index
            while index < len(text) and _is_ascii_alnum(text[index]):
                index += 1
                col += 1
            while index < len(text) and text[index] == ".":
                dot_line, dot_col = line, col
                index += 1
                col += 1
                if index >= len(text) or not _is_ascii_letter(text[index]):
                    raise ExpressionParseError(
                        "invalid dotted identifier", line=dot_line, col=dot_col
                    )
                while index < len(text) and _is_ascii_alnum(text[index]):
                    index += 1
                    col += 1
            identifier_text = text[begin:index]
            upper = identifier_text.upper()
            kind = upper if "." not in identifier_text and upper in _KEYWORDS else "IDENT"
            tokens.append(
                _Token(kind, upper if kind != "IDENT" else identifier_text, start_line, start_col)
            )
            continue
        two = text[index : index + 2]
        if two in {">=", "<=", "!="}:
            tokens.append(_Token("OP", two, start_line, start_col))
            index += 2
            col += 2
            continue
        if char in "=><+-*/(),":
            kind = {"(": "LPAREN", ")": "RPAREN", ",": "COMMA"}.get(char, "OP")
            tokens.append(_Token(kind, char, start_line, start_col))
            index += 1
            col += 1
            continue
        raise ExpressionParseError("unsupported character", line=start_line, col=start_col)
    tokens.append(_Token("EOF", "", line, col))
    return tokens


class _Parser:
    def __init__(self, text: str) -> None:
        self.tokens = _tokenize(text)
        self.index = 0
        self.node_count = 0
        self.parenthesis_depth = 0

    @property
    def current(self) -> _Token:
        return self.tokens[self.index]

    def _advance(self) -> _Token:
        token = self.current
        self.index += 1
        return token

    def _accept(self, kind: str, value: str | None = None) -> _Token | None:
        token = self.current
        if token.kind != kind or (value is not None and token.value != value):
            return None
        return self._advance()

    def _expect(self, kind: str, value: str | None = None) -> _Token:
        token = self._accept(kind, value)
        if token is None:
            expected = value or kind
            raise ExpressionParseError(
                f"expected {expected}", line=self.current.line, col=self.current.col
            )
        return token

    def _node(self, node: ExprNode) -> ExprNode:
        self.node_count += 1
        if self.node_count > MAX_AST_NODES:
            raise ExpressionParseError(
                f"expression exceeds {MAX_AST_NODES} AST nodes",
                line=self.current.line,
                col=self.current.col,
            )
        return node

    def parse(self) -> ParsedExpression:
        root = self._parse_expression()
        self._expect("EOF")
        depth = _ast_depth(root)
        if depth > MAX_AST_DEPTH:
            raise ExpressionParseError(f"expression exceeds AST depth {MAX_AST_DEPTH}")
        references = tuple(sorted(_collect_identifiers(root)))
        return ParsedExpression(
            root=root,
            referenced_features=references,
            normalized_preview=render_expression(root),
            node_count=self.node_count,
        )

    def _parse_expression(self) -> ExprNode:
        if self.current.kind == "CASE":
            return self._parse_case()
        return self._parse_or()

    def _parse_case(self) -> ExprNode:
        token = self._expect("CASE")
        branches: list[CaseBranch] = []
        while self._accept("WHEN") is not None:
            if len(branches) >= MAX_CASE_BRANCHES:
                raise ExpressionParseError(
                    f"CASE exceeds {MAX_CASE_BRANCHES} branches", line=token.line, col=token.col
                )
            when = self._parse_or()
            self._expect("THEN")
            then = self._parse_or()
            branches.append(CaseBranch(when=when, then=then))
        if not branches:
            raise ExpressionParseError(
                "CASE requires at least one WHEN", line=token.line, col=token.col
            )
        default = self._parse_or() if self._accept("ELSE") is not None else None
        self._expect("END")
        return self._node(CaseNode(kind="case", branches=tuple(branches), default=default))

    def _parse_or(self) -> ExprNode:
        node = self._parse_and()
        while self._accept("OR") is not None:
            node = self._node(
                BinaryNode(kind="binary", operator="OR", left=node, right=self._parse_and())
            )
        return node

    def _parse_and(self) -> ExprNode:
        node = self._parse_not()
        while self._accept("AND") is not None:
            node = self._node(
                BinaryNode(kind="binary", operator="AND", left=node, right=self._parse_not())
            )
        return node

    def _parse_not(self) -> ExprNode:
        if self._accept("NOT") is not None:
            return self._node(UnaryNode(kind="unary", operator="NOT", operand=self._parse_not()))
        return self._parse_comparison()

    def _parse_comparison(self) -> ExprNode:
        node = self._parse_additive()
        if self.current.kind == "OP" and self.current.value in _COMPARISONS:
            operator = cast(Literal["=", "!=", ">", ">=", "<", "<="], self._advance().value)
            return self._node(
                BinaryNode(
                    kind="binary", operator=operator, left=node, right=self._parse_additive()
                )
            )
        negated = False
        if self.current.kind == "NOT" and self.tokens[self.index + 1].kind == "IN":
            self._advance()
            self._advance()
            negated = True
        elif self._accept("IN") is not None:
            negated = False
        else:
            if self._accept("IS") is not None:
                is_negated = self._accept("NOT") is not None
                self._expect("NULL")
                return self._node(IsNullNode(kind="is_null", operand=node, negated=is_negated))
            return node
        self._expect("LPAREN")
        values: list[LiteralNode] = [self._parse_literal()]
        while self._accept("COMMA") is not None:
            if len(values) >= MAX_LIST_ITEMS:
                raise ExpressionParseError(f"IN list exceeds {MAX_LIST_ITEMS} items")
            values.append(self._parse_literal())
        self._expect("RPAREN")
        return self._node(InNode(kind="in", operand=node, values=tuple(values), negated=negated))

    def _parse_additive(self) -> ExprNode:
        node = self._parse_multiplicative()
        while self.current.kind == "OP" and self.current.value in {"+", "-"}:
            operator = cast(Literal["+", "-"], self._advance().value)
            node = self._node(
                BinaryNode(
                    kind="binary", operator=operator, left=node, right=self._parse_multiplicative()
                )
            )
        return node

    def _parse_multiplicative(self) -> ExprNode:
        node = self._parse_unary()
        while self.current.kind == "OP" and self.current.value in {"*", "/"}:
            operator = cast(Literal["*", "/"], self._advance().value)
            node = self._node(
                BinaryNode(kind="binary", operator=operator, left=node, right=self._parse_unary())
            )
        return node

    def _parse_unary(self) -> ExprNode:
        if self._accept("OP", "-") is not None:
            return self._node(UnaryNode(kind="unary", operator="-", operand=self._parse_unary()))
        return self._parse_primary()

    def _parse_primary(self) -> ExprNode:
        if self.current.kind in {"NUMBER", "STRING", "TRUE", "FALSE", "NULL"}:
            return self._parse_literal()
        if self.current.kind == "CASE":
            return self._parse_case()
        if self.current.kind == "IDENT":
            token = self._advance()
            if self._accept("LPAREN") is not None:
                function_name = token.value.upper()
                if function_name not in _FUNCTIONS:
                    raise ExpressionParseError(
                        "function is not allowed", line=token.line, col=token.col
                    )
                arguments: list[ExprNode] = []
                if self.current.kind != "RPAREN":
                    arguments.append(self._parse_expression())
                    while self._accept("COMMA") is not None:
                        arguments.append(self._parse_expression())
                self._expect("RPAREN")
                _validate_function_arity(function_name, len(arguments), token.line, token.col)
                return self._node(
                    FunctionNode(
                        kind="function",
                        name=cast(Literal["MIN", "MAX", "ROUND", "ABS", "COALESCE"], function_name),
                        arguments=tuple(arguments),
                    )
                )
            return self._node(IdentifierNode(kind="identifier", path=token.value))
        if self._accept("LPAREN") is not None:
            self.parenthesis_depth += 1
            if self.parenthesis_depth > MAX_AST_DEPTH:
                raise ExpressionParseError(f"expression exceeds nesting depth {MAX_AST_DEPTH}")
            node = self._parse_expression()
            self._expect("RPAREN")
            self.parenthesis_depth -= 1
            return node
        raise ExpressionParseError(
            "expected expression", line=self.current.line, col=self.current.col
        )

    def _parse_literal(self) -> LiteralNode:
        token = self.current
        if token.kind == "NUMBER":
            self._advance()
            value: Scalar = float(token.value) if "." in token.value else int(token.value)
        elif token.kind == "STRING":
            self._advance()
            value = token.value
        elif token.kind == "TRUE":
            self._advance()
            value = True
        elif token.kind == "FALSE":
            self._advance()
            value = False
        elif token.kind == "NULL":
            self._advance()
            value = None
        else:
            raise ExpressionParseError("expected literal", line=token.line, col=token.col)
        return cast(LiteralNode, self._node(LiteralNode(kind="literal", value=value)))


def _validate_function_arity(name: str, count: int, line: int, col: int) -> None:
    valid = (
        (name in {"ABS"} and count == 1)
        or (name == "ROUND" and count in {1, 2})
        or (name in {"MIN", "MAX", "COALESCE"} and count >= 1)
    )
    if not valid:
        raise ExpressionParseError("invalid function argument count", line=line, col=col)


def parse_expression(text: str) -> ParsedExpression:
    return _Parser(text).parse()


def validate_expression(
    text: str,
    feature_types: Mapping[str, str],
    *,
    expects: Literal["value", "boolean"] = "value",
) -> ValidatedExpression:
    parsed = parse_expression(text)
    unknown = [path for path in parsed.referenced_features if path not in feature_types]
    if unknown:
        raise ExpressionValidationError(f"unknown feature: {unknown[0]}")
    inferred = _validate_semantics(parsed.root, feature_types)
    if expects == "boolean" and inferred not in {"BOOLEAN", "NULL", "UNKNOWN"}:
        raise ExpressionValidationError("expression does not produce a boolean value")
    return ValidatedExpression(
        root=parsed.root,
        referenced_features=parsed.referenced_features,
        normalized_preview=parsed.normalized_preview,
        node_count=parsed.node_count,
        inferred_type=inferred,
    )


def _compatible_types(left: ExpressionType, right: ExpressionType) -> bool:
    if left in {"NULL", "UNKNOWN"} or right in {"NULL", "UNKNOWN"}:
        return True
    return left == right


def _require_static_type(
    actual: ExpressionType,
    expected: set[ExpressionType],
    message: str,
) -> None:
    if actual not in expected | {"NULL", "UNKNOWN"}:
        raise ExpressionValidationError(message)


def _validate_semantics(node: ExprNode, feature_types: Mapping[str, str]) -> ExpressionType:
    if isinstance(node, (LiteralNode, IdentifierNode)):
        return infer_expression_type(node, feature_types)
    if isinstance(node, UnaryNode):
        operand_type = _validate_semantics(node.operand, feature_types)
        if node.operator == "NOT":
            _require_static_type(operand_type, {"BOOLEAN"}, "NOT requires a boolean operand")
            return "BOOLEAN"
        _require_static_type(operand_type, {"NUMBER"}, "unary minus requires a numeric operand")
        return "NUMBER"
    if isinstance(node, IsNullNode):
        _validate_semantics(node.operand, feature_types)
        return "BOOLEAN"
    if isinstance(node, InNode):
        operand_type = _validate_semantics(node.operand, feature_types)
        for item in node.values:
            item_type = _validate_semantics(item, feature_types)
            if not _compatible_types(operand_type, item_type):
                raise ExpressionValidationError("IN list value type does not match operand")
        return "BOOLEAN"
    if isinstance(node, BinaryNode):
        left_type = _validate_semantics(node.left, feature_types)
        right_type = _validate_semantics(node.right, feature_types)
        if node.operator in {"AND", "OR"}:
            _require_static_type(
                left_type, {"BOOLEAN"}, f"{node.operator} requires boolean operands"
            )
            _require_static_type(
                right_type, {"BOOLEAN"}, f"{node.operator} requires boolean operands"
            )
            return "BOOLEAN"
        if node.operator in {"+", "-", "*", "/"}:
            _require_static_type(left_type, {"NUMBER"}, "arithmetic requires numeric operands")
            _require_static_type(right_type, {"NUMBER"}, "arithmetic requires numeric operands")
            return "NUMBER"
        if not _compatible_types(left_type, right_type):
            raise ExpressionValidationError("comparison operands have incompatible types")
        if node.operator in {">", ">=", "<", "<="}:
            allowed: set[ExpressionType] = {"NUMBER", "STRING"}
            _require_static_type(
                left_type, allowed, "ordered comparison requires numbers or strings"
            )
            _require_static_type(
                right_type, allowed, "ordered comparison requires numbers or strings"
            )
        return "BOOLEAN"
    if isinstance(node, FunctionNode):
        argument_types = [_validate_semantics(item, feature_types) for item in node.arguments]
        if node.name in {"ABS", "ROUND", "MIN", "MAX"}:
            for argument_type in argument_types:
                _require_static_type(
                    argument_type, {"NUMBER"}, f"{node.name} requires numeric arguments"
                )
            return "NUMBER"
        concrete = {item for item in argument_types if item not in {"NULL", "UNKNOWN"}}
        if len(concrete) > 1:
            raise ExpressionValidationError("COALESCE arguments have incompatible types")
        return next(iter(concrete), "UNKNOWN")
    result_types: list[ExpressionType] = []
    for branch in node.branches:
        when_type = _validate_semantics(branch.when, feature_types)
        _require_static_type(when_type, {"BOOLEAN"}, "CASE WHEN requires a boolean condition")
        result_types.append(_validate_semantics(branch.then, feature_types))
    if node.default is not None:
        result_types.append(_validate_semantics(node.default, feature_types))
    concrete = {item for item in result_types if item not in {"NULL", "UNKNOWN"}}
    if len(concrete) > 1:
        raise ExpressionValidationError("CASE result branches have incompatible types")
    return next(iter(concrete), "UNKNOWN")


def infer_expression_type(node: ExprNode, feature_types: Mapping[str, str]) -> ExpressionType:
    if isinstance(node, LiteralNode):
        if node.value is None:
            return "NULL"
        if isinstance(node.value, bool):
            return "BOOLEAN"
        if isinstance(node.value, (int, float)):
            return "NUMBER"
        return "STRING"
    if isinstance(node, IdentifierNode):
        value = feature_types.get(node.path, "UNKNOWN").upper()
        return cast(
            ExpressionType, value if value in {"NUMBER", "STRING", "BOOLEAN", "NULL"} else "UNKNOWN"
        )
    if isinstance(node, UnaryNode):
        return "BOOLEAN" if node.operator == "NOT" else "NUMBER"
    if isinstance(node, (IsNullNode, InNode)):
        return "BOOLEAN"
    if isinstance(node, BinaryNode):
        if node.operator in {"OR", "AND", "=", "!=", ">", ">=", "<", "<="}:
            return "BOOLEAN"
        return "NUMBER"
    if isinstance(node, FunctionNode):
        if node.name in {"ROUND", "ABS", "MIN", "MAX"}:
            return "NUMBER"
        result_types = [infer_expression_type(item, feature_types) for item in node.arguments]
        return next((item for item in result_types if item not in {"NULL", "UNKNOWN"}), "UNKNOWN")
    result_types = [infer_expression_type(branch.then, feature_types) for branch in node.branches]
    if node.default is not None:
        result_types.append(infer_expression_type(node.default, feature_types))
    concrete = {item for item in result_types if item not in {"NULL", "UNKNOWN"}}
    return concrete.pop() if len(concrete) == 1 else "UNKNOWN"


def evaluate_expression(node: ExprNode, features: Mapping[str, object]) -> Scalar:
    """Interpret a validated tree without ambient capabilities or side effects."""

    try:
        result = _evaluate(node, features)
        # Even finite JSON inputs can overflow (e.g. 1e308 * 1e308).
        # Never allow NaN/Infinity/huge integers to propagate to a trace or JSONB.
        if isinstance(result, (int, float)) and not isinstance(result, bool):
            if not finite_number(result):
                raise ExpressionEvaluationError("expression produced a non-finite number")
        return result
    except ExpressionEvaluationError:
        raise
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise ExpressionEvaluationError("expression evaluation failed") from exc


def _evaluate(node: ExprNode, features: Mapping[str, object]) -> Scalar:
    if isinstance(node, LiteralNode):
        return node.value
    if isinstance(node, IdentifierNode):
        value = features.get(node.path)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            _checked_number(value)
        return value if isinstance(value, (int, float, str, bool)) or value is None else None
    if isinstance(node, UnaryNode):
        value = _evaluate(node.operand, features)
        if node.operator == "NOT":
            return None if value is None else not _require_bool(value)
        if value is None:
            return None
        return -_require_number(value)
    if isinstance(node, IsNullNode):
        result = _evaluate(node.operand, features) is None
        return not result if node.negated else result
    if isinstance(node, InNode):
        value = _evaluate(node.operand, features)
        if value is None:
            return None
        # Python treats True == 1 and False == 0. Rule membership must not
        # silently mix boolean and numeric feature domains.
        choices = [item.value for item in node.values]
        result = any(_typed_equal(value, choice) for choice in choices)
        return not result if node.negated else result
    if isinstance(node, BinaryNode):
        if node.operator in {"AND", "OR"}:
            left = _evaluate(node.left, features)
            # SQL three-valued logic permits these results without evaluating
            # the other operand. The skipped side may otherwise raise (e.g. / 0).
            if node.operator == "AND" and left is False:
                return False
            if node.operator == "OR" and left is True:
                return True
            right = _evaluate(node.right, features)
            return _tri_logic(node.operator, left, right)
        left = _evaluate(node.left, features)
        right = _evaluate(node.right, features)
        if left is None or right is None:
            return None
        if node.operator in _COMPARISONS:
            return _compare(node.operator, left, right)
        left_number = _require_number(left)
        right_number = _require_number(right)
        if node.operator == "+":
            return _checked_number(left_number + right_number)
        if node.operator == "-":
            return _checked_number(left_number - right_number)
        if node.operator == "*":
            return _checked_number(left_number * right_number)
        if right_number == 0:
            raise ExpressionEvaluationError("expression division by zero")
        return _checked_number(left_number / right_number)
    if isinstance(node, FunctionNode):
        if node.name == "COALESCE":
            # COALESCE is lazy: later fallback expressions must not run once
            # the first non-null value has been found.
            for argument in node.arguments:
                value = _evaluate(argument, features)
                if value is not None:
                    return value
            return None
        values = [_evaluate(argument, features) for argument in node.arguments]
        if any(value is None for value in values):
            return None
        numbers = [_require_number(value) for value in values]
        if node.name == "ABS":
            return abs(numbers[0])
        if node.name == "ROUND":
            digits = int(numbers[1]) if len(numbers) == 2 else 0
            return round(numbers[0], digits)
        return min(numbers) if node.name == "MIN" else max(numbers)
    for branch in node.branches:
        condition = _evaluate(branch.when, features)
        if condition is None:
            continue
        if not isinstance(condition, bool):
            raise ExpressionEvaluationError("CASE WHEN must evaluate to boolean")
        if condition:
            return _evaluate(branch.then, features)
    return _evaluate(node.default, features) if node.default is not None else None


def _checked_number(value: int | float) -> int | float:
    if not finite_number(value):
        raise ExpressionEvaluationError("expression produced a non-finite number")
    return value


def _require_number(value: Scalar) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExpressionEvaluationError("numeric expression type error")
    return _checked_number(value)


def _require_bool(value: Scalar) -> bool:
    if not isinstance(value, bool):
        raise ExpressionEvaluationError("boolean expression type error")
    return value


def _tri_logic(operator: str, left: Scalar, right: Scalar) -> bool | None:
    left_bool = None if left is None else _require_bool(left)
    right_bool = None if right is None else _require_bool(right)
    if operator == "AND":
        if left_bool is False or right_bool is False:
            return False
        if left_bool is None or right_bool is None:
            return None
        return True
    if left_bool is True or right_bool is True:
        return True
    if left_bool is None or right_bool is None:
        return None
    return False


def _typed_equal(left: Scalar, right: Scalar) -> bool:
    """Compare JSON scalar values without Python's bool/int coercion."""
    if type(left) is type(right):
        return bool(left == right)
    both_numbers = (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    )
    return bool(left == right) if both_numbers else False


def _compare(operator: str, left: Scalar, right: Scalar) -> bool:
    if type(left) is not type(right) and not (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ):
        raise ExpressionEvaluationError("comparison type error")
    if operator == "=":
        return _typed_equal(left, right)
    if operator == "!=":
        return not _typed_equal(left, right)
    try:
        if operator == ">":
            return left > right  # type: ignore[operator]
        if operator == ">=":
            return left >= right  # type: ignore[operator]
        if operator == "<":
            return left < right  # type: ignore[operator]
        return left <= right  # type: ignore[operator]
    except TypeError as exc:
        raise ExpressionEvaluationError("comparison type error") from exc


def _ast_depth(node: ExprNode) -> int:
    if isinstance(node, (LiteralNode, IdentifierNode)):
        return 1
    if isinstance(node, (UnaryNode, IsNullNode)):
        return 1 + _ast_depth(node.operand)
    if isinstance(node, InNode):
        return 1 + max([_ast_depth(node.operand), *(_ast_depth(item) for item in node.values)])
    if isinstance(node, BinaryNode):
        return 1 + max(_ast_depth(node.left), _ast_depth(node.right))
    if isinstance(node, FunctionNode):
        return 1 + max(_ast_depth(item) for item in node.arguments)
    values = [item for branch in node.branches for item in (branch.when, branch.then)]
    if node.default is not None:
        values.append(node.default)
    return 1 + max(_ast_depth(item) for item in values)


def _collect_identifiers(node: ExprNode) -> set[str]:
    if isinstance(node, IdentifierNode):
        return {node.path}
    if isinstance(node, LiteralNode):
        return set()
    if isinstance(node, (UnaryNode, IsNullNode)):
        return _collect_identifiers(node.operand)
    if isinstance(node, InNode):
        return _collect_identifiers(node.operand)
    if isinstance(node, BinaryNode):
        return _collect_identifiers(node.left) | _collect_identifiers(node.right)
    if isinstance(node, FunctionNode):
        return set().union(*(_collect_identifiers(item) for item in node.arguments))
    values = [item for branch in node.branches for item in (branch.when, branch.then)]
    if node.default is not None:
        values.append(node.default)
    return set().union(*(_collect_identifiers(item) for item in values))


def ast_to_json(node: ExprNode) -> dict[str, object]:
    if isinstance(node, LiteralNode):
        return {"kind": node.kind, "value": node.value}
    if isinstance(node, IdentifierNode):
        return {"kind": node.kind, "path": node.path}
    if isinstance(node, UnaryNode):
        return {"kind": node.kind, "operator": node.operator, "operand": ast_to_json(node.operand)}
    if isinstance(node, BinaryNode):
        return {
            "kind": node.kind,
            "operator": node.operator,
            "left": ast_to_json(node.left),
            "right": ast_to_json(node.right),
        }
    if isinstance(node, IsNullNode):
        return {"kind": node.kind, "operand": ast_to_json(node.operand), "negated": node.negated}
    if isinstance(node, InNode):
        return {
            "kind": node.kind,
            "operand": ast_to_json(node.operand),
            "values": [ast_to_json(item) for item in node.values],
            "negated": node.negated,
        }
    if isinstance(node, FunctionNode):
        return {
            "kind": node.kind,
            "name": node.name,
            "arguments": [ast_to_json(item) for item in node.arguments],
        }
    return {
        "kind": node.kind,
        "branches": [
            {"when": ast_to_json(branch.when), "then": ast_to_json(branch.then)}
            for branch in node.branches
        ],
        "default": ast_to_json(node.default) if node.default is not None else None,
    }


def ast_from_json(value: Mapping[str, object]) -> ExprNode:
    """Rebuild and limit-check a stored tree before every execution."""

    count = 0

    def build(raw: Mapping[str, object], depth: int) -> ExprNode:
        nonlocal count
        count += 1
        if count > MAX_AST_NODES or depth > MAX_AST_DEPTH:
            raise ExpressionValidationError("stored expression exceeds safety limits")
        kind = raw.get("kind")
        if kind == "literal":
            scalar = raw.get("value")
            if not (isinstance(scalar, (int, float, str, bool)) or scalar is None):
                raise ExpressionValidationError("stored expression literal is invalid")
            return LiteralNode(kind="literal", value=scalar)
        if kind == "identifier":
            path = raw.get("path")
            if not isinstance(path, str):
                raise ExpressionValidationError("stored expression identifier is invalid")
            return IdentifierNode(kind="identifier", path=path)
        if kind == "unary":
            operator = raw.get("operator")
            operand = raw.get("operand")
            if operator not in {"NOT", "-"} or not isinstance(operand, Mapping):
                raise ExpressionValidationError("stored unary expression is invalid")
            return UnaryNode(
                kind="unary",
                operator=cast(Literal["NOT", "-"], operator),
                operand=build(cast(Mapping[str, object], operand), depth + 1),
            )
        if kind == "binary":
            operator = raw.get("operator")
            left, right = raw.get("left"), raw.get("right")
            allowed = {"OR", "AND", "=", "!=", ">", ">=", "<", "<=", "+", "-", "*", "/"}
            if (
                operator not in allowed
                or not isinstance(left, Mapping)
                or not isinstance(right, Mapping)
            ):
                raise ExpressionValidationError("stored binary expression is invalid")
            return BinaryNode(
                kind="binary",
                operator=cast(
                    Literal["OR", "AND", "=", "!=", ">", ">=", "<", "<=", "+", "-", "*", "/"],
                    operator,
                ),
                left=build(cast(Mapping[str, object], left), depth + 1),
                right=build(cast(Mapping[str, object], right), depth + 1),
            )
        if kind == "is_null":
            operand = raw.get("operand")
            negated = raw.get("negated")
            if not isinstance(operand, Mapping) or not isinstance(negated, bool):
                raise ExpressionValidationError("stored null expression is invalid")
            return IsNullNode(
                kind="is_null",
                operand=build(cast(Mapping[str, object], operand), depth + 1),
                negated=negated,
            )
        if kind == "in":
            operand, values, negated = raw.get("operand"), raw.get("values"), raw.get("negated")
            if (
                not isinstance(operand, Mapping)
                or not isinstance(values, list)
                or len(values) > MAX_LIST_ITEMS
                or not isinstance(negated, bool)
            ):
                raise ExpressionValidationError("stored IN expression is invalid")
            built_values: list[LiteralNode] = []
            for item in values:
                if not isinstance(item, Mapping):
                    raise ExpressionValidationError("stored IN literal is invalid")
                built = build(cast(Mapping[str, object], item), depth + 1)
                if not isinstance(built, LiteralNode):
                    raise ExpressionValidationError("stored IN value must be literal")
                built_values.append(built)
            return InNode(
                kind="in",
                operand=build(cast(Mapping[str, object], operand), depth + 1),
                values=tuple(built_values),
                negated=negated,
            )
        if kind == "function":
            name, arguments = raw.get("name"), raw.get("arguments")
            if name not in _FUNCTIONS or not isinstance(arguments, list):
                raise ExpressionValidationError("stored function expression is invalid")
            _validate_function_arity(str(name), len(arguments), 1, 1)
            if not all(isinstance(item, Mapping) for item in arguments):
                raise ExpressionValidationError("stored function argument is invalid")
            return FunctionNode(
                kind="function",
                name=cast(Literal["MIN", "MAX", "ROUND", "ABS", "COALESCE"], name),
                arguments=tuple(
                    build(cast(Mapping[str, object], item), depth + 1) for item in arguments
                ),
            )
        if kind == "case":
            branches, default = raw.get("branches"), raw.get("default")
            if not isinstance(branches, list) or not 1 <= len(branches) <= MAX_CASE_BRANCHES:
                raise ExpressionValidationError("stored CASE expression is invalid")
            built_branches: list[CaseBranch] = []
            for branch in branches:
                if not isinstance(branch, Mapping):
                    raise ExpressionValidationError("stored CASE branch is invalid")
                when, then = branch.get("when"), branch.get("then")
                if not isinstance(when, Mapping) or not isinstance(then, Mapping):
                    raise ExpressionValidationError("stored CASE branch is invalid")
                built_branches.append(
                    CaseBranch(
                        when=build(cast(Mapping[str, object], when), depth + 1),
                        then=build(cast(Mapping[str, object], then), depth + 1),
                    )
                )
            if default is not None and not isinstance(default, Mapping):
                raise ExpressionValidationError("stored CASE default is invalid")
            return CaseNode(
                kind="case",
                branches=tuple(built_branches),
                default=(
                    build(cast(Mapping[str, object], default), depth + 1)
                    if isinstance(default, Mapping)
                    else None
                ),
            )
        raise ExpressionValidationError("stored expression node kind is invalid")

    return build(value, 1)


def render_expression(node: ExprNode) -> str:
    if isinstance(node, LiteralNode):
        if node.value is None:
            return "NULL"
        if node.value is True:
            return "TRUE"
        if node.value is False:
            return "FALSE"
        if isinstance(node.value, str):
            return "'" + node.value.replace("'", "''") + "'"
        return str(node.value)
    if isinstance(node, IdentifierNode):
        return node.path
    if isinstance(node, UnaryNode):
        prefix = "NOT " if node.operator == "NOT" else "-"
        return f"{prefix}({render_expression(node.operand)})"
    if isinstance(node, BinaryNode):
        return f"({render_expression(node.left)} {node.operator} {render_expression(node.right)})"
    if isinstance(node, IsNullNode):
        return f"({render_expression(node.operand)} IS {'NOT ' if node.negated else ''}NULL)"
    if isinstance(node, InNode):
        values = ", ".join(render_expression(value) for value in node.values)
        return f"({render_expression(node.operand)} {'NOT ' if node.negated else ''}IN ({values}))"
    if isinstance(node, FunctionNode):
        return f"{node.name}({', '.join(render_expression(item) for item in node.arguments)})"
    parts = ["CASE"]
    for branch in node.branches:
        parts.append(f"WHEN {render_expression(branch.when)} THEN {render_expression(branch.then)}")
    if node.default is not None:
        parts.append(f"ELSE {render_expression(node.default)}")
    parts.append("END")
    return " ".join(parts)
