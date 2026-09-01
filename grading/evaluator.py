"""Declarative, non-executing evaluator for the first AulaWeb milestone.

Student files are parsed as data.  The evaluator never imports, evaluates or
executes JavaScript, Bash or Python and never renders student HTML in the
Django process.  Bash is inspected with tree-sitter's Bash grammar and Python
with the standard-library AST parser; no shell, subprocess, network or
filesystem access is available to submitted source.
Public browser tests may offer richer feedback in the isolated preview, but
only this static evaluator can contribute to an official MVP score.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Iterable

import esprima
import tinycss2
import tree_sitter_bash
from bs4 import BeautifulSoup
from tree_sitter import Language, Parser

MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 1024 * 1024
MAX_SELECTOR_LENGTH = 500
MAX_TESTS = 200
MAX_NODES = 20_000
MAX_BASH_NODES = 5_000
MAX_BASH_DEPTH = 80
MAX_PYTHON_NODES = 5_000
MAX_PYTHON_DEPTH = 80
EVALUATOR_VERSION = "static-v4"

FILE_ALIASES = {"html": "html", "css": "css", "js": "javascript", "javascript": "javascript"}
WEB_FILE_KEYS = ("html", "css", "javascript")
BASH_FILE_KEYS = ("bash",)
SUPPORTED_TYPES = {
    "html.selector_exists",
    "html.selector_count",
    "html.text_contains",
    "html.attribute_equals",
    "html.element_order",
    "html.forbidden_element_absent",
    "css.selector_exists",
    "css.declaration_equals",
    "css.media_query_exists",
    "css.forbidden_declaration_absent",
    "js.function_declared",
    "js.variable_declared",
    "js.event_listener_registered",
    "js.syntax_valid",
    "js.forbidden_api_absent",
    "bash.syntax_valid",
    "bash.shebang",
    "bash.command_used",
    "bash.variable_assigned",
    "bash.node_kind",
    "python.syntax_valid",
    "python.assignment",
    # Keep the explicit name as an ergonomic alias for teacher-authored
    # catalogues that mirror the Bash DSL.
    "python.variable_assigned",
    "python.function_declared",
    "python.node_kind",
    "python.call_used",
    "python.import_used",
    "python.file_opened",
    "python.attribute_used",
    "python.subscript_used",
    "python.dict_keys",
    "python.loop_target",
    "python.exception_handled",
    "python.comparison_used",
}

_REQUIRED = {
    "html.selector_exists": {"selector"},
    "html.selector_count": {"selector", "expected"},
    "html.text_contains": {"selector", "expected"},
    "html.attribute_equals": {"selector", "attribute", "expected"},
    "html.element_order": {"first", "second"},
    "html.forbidden_element_absent": {"selector"},
    "css.selector_exists": {"selector"},
    "css.declaration_equals": {"selector", "property", "expected"},
    "css.media_query_exists": {"query"},
    "css.forbidden_declaration_absent": {"property"},
    "js.function_declared": {"name"},
    "js.variable_declared": {"name"},
    "js.event_listener_registered": {"event"},
    "js.syntax_valid": set(),
    "js.forbidden_api_absent": {"api"},
    "bash.syntax_valid": set(),
    "bash.shebang": set(),
    "bash.command_used": {"command"},
    "bash.variable_assigned": {"name"},
    "bash.node_kind": {"kind"},
    "python.syntax_valid": set(),
    "python.assignment": {"name"},
    "python.variable_assigned": {"name"},
    "python.function_declared": {"name"},
    "python.node_kind": {"kind"},
    "python.call_used": {"name"},
    "python.import_used": {"module"},
    "python.file_opened": set(),
    "python.attribute_used": {"name"},
    "python.subscript_used": {"name", "key"},
    "python.dict_keys": {"name", "keys"},
    "python.loop_target": {"name"},
    "python.exception_handled": {"name"},
    "python.comparison_used": {"operator"},
}
_OPTIONAL_BY_TYPE = {
    **{test_type: {"selector", "expected", "attribute", "first", "second", "query", "property", "name", "event", "target", "api"} for test_type in SUPPORTED_TYPES if not test_type.startswith("bash.")},
    "bash.syntax_valid": set(),
    "bash.shebang": {"expected", "interpreter"},
    "bash.command_used": {"command", "args"},
    "bash.variable_assigned": {"name"},
    "bash.node_kind": {"kind"},
    "python.syntax_valid": set(),
    "python.assignment": {"name"},
    "python.variable_assigned": {"name"},
    "python.function_declared": {"name", "args", "returns"},
    "python.node_kind": {"kind", "non_empty"},
    "python.call_used": {"name", "args", "arg_names"},
    "python.import_used": {"module"},
    "python.file_opened": {"mode", "context_manager", "encoding", "body_non_empty"},
    "python.attribute_used": {"name"},
    "python.subscript_used": {"name", "key"},
    "python.dict_keys": {"name", "keys"},
    "python.loop_target": {"name", "iterable"},
    "python.exception_handled": {"name"},
    "python.comparison_used": {"operator", "left", "right"},
}

BASH_NODE_KIND_ALIASES = {
    "if": "if_statement",
    "for": "for_statement",
    "while": "while_statement",
    "function": "function_definition",
    "pipeline": "pipeline",
    "case": "case_statement",
    "command": "command",
    "list": "list",
    "if_statement": "if_statement",
    "for_statement": "for_statement",
    "while_statement": "while_statement",
    "function_definition": "function_definition",
    "case_statement": "case_statement",
    "variable_assignment": "variable_assignment",
    "redirected_statement": "redirected_statement",
}

PYTHON_FILE_KEYS = ("python",)
PYTHON_FILE_ALIASES = {"python": "python", "main.py": "python"}
PYTHON_NODE_KIND_ALIASES = {
    # Control flow aliases used by the catalogue and teacher-authored tests.
    "if": "If",
    "if_statement": "If",
    "for": "For",
    "for_statement": "For",
    "while": "While",
    "while_statement": "While",
    "try": "Try",
    "try_statement": "Try",
    "with": "With",
    "with_statement": "With",
    "match": "Match",
    "match_statement": "Match",
    "function": "FunctionDef",
    "function_definition": "FunctionDef",
    "async_function": "AsyncFunctionDef",
    "async_for": "AsyncFor",
    "async_with": "AsyncWith",
    # Common data and expression nodes useful for small, structural exercises.
    "assignment": "Assign",
    "assign": "Assign",
    "annotated_assignment": "AnnAssign",
    "augmented_assignment": "AugAssign",
    "call": "Call",
    "dict": "Dict",
    "list": "List",
    "tuple": "Tuple",
    "set": "Set",
    "import": "Import",
    "import_from": "ImportFrom",
    "f_string": "JoinedStr",
    "fstring": "JoinedStr",
    "return": "Return",
    "return_statement": "Return",
    "except": "ExceptHandler",
    "except_handler": "ExceptHandler",
    "comparison": "Compare",
    "if_else": "__if_else__",
    "if_else_statement": "__if_else__",
}
PYTHON_MODES = frozenset({"r", "w", "a", "x", "r+", "w+", "a+", "x+", "rb", "wb", "ab", "xb", "r+b", "w+b", "a+b", "x+b"})
PYTHON_COMPARISON_ALIASES = {
    "eq": "Eq",
    "==": "Eq",
    "ne": "NotEq",
    "!=": "NotEq",
    "lt": "Lt",
    "<": "Lt",
    "lte": "LtE",
    "<=": "LtE",
    "gt": "Gt",
    ">": "Gt",
    "gte": "GtE",
    ">=": "GtE",
    "in": "In",
    "not_in": "NotIn",
    "not in": "NotIn",
    "is": "Is",
    "is_not": "IsNot",
    "is not": "IsNot",
}


class EvaluatorValidationError(ValueError):
    pass


class EvaluatorInfrastructureError(RuntimeError):
    pass


@dataclass(frozen=True)
class EvaluationResult:
    name: str
    type: str
    passed: bool
    status: str
    points: Decimal
    earned_points: Decimal
    feedback: str
    detail: dict[str, Any]

    def as_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "passed": self.passed,
            "status": self.status,
            "points": str(self.points),
            "earned_points": str(self.earned_points),
            "feedback": self.feedback,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class EvaluationReport:
    status: str
    score: Decimal | None
    passed_points: Decimal
    total_points: Decimal
    results: list[EvaluationResult]
    error_message: str = ""

    def as_dict(self):
        return {
            "status": self.status,
            "score": str(self.score) if self.score is not None else None,
            "passed_points": str(self.passed_points),
            "total_points": str(self.total_points),
            "results": [result.as_dict() for result in self.results],
            "error_message": self.error_message,
            "evaluator_version": EVALUATOR_VERSION,
        }


def _normalise_files(files: dict[str, Any], *, language: str = "web") -> dict[str, str]:
    if not isinstance(files, dict):
        raise EvaluatorValidationError("Los archivos deben recibirse como un objeto JSON.")
    if language not in {"web", "bash", "python"}:
        raise EvaluatorValidationError("El lenguaje de la actividad no es válido.")
    if language == "bash":
        allowed_keys = set(BASH_FILE_KEYS)
    elif language == "python":
        allowed_keys = set(PYTHON_FILE_KEYS)
    else:
        allowed_keys = set(WEB_FILE_KEYS)
    normalised: dict[str, str] = {key: "" for key in allowed_keys}
    total = 0
    for raw_name, raw_content in files.items():
        if raw_name in {"revision", "csrfmiddlewaretoken"}:
            continue
        raw_key = str(raw_name).lower()
        if language == "bash":
            name = "bash" if raw_key == "bash" else None
        elif language == "python":
            name = PYTHON_FILE_ALIASES.get(raw_key)
        else:
            name = FILE_ALIASES.get(raw_key)
        if name is None or name not in allowed_keys:
            expected = {
                "bash": "Bash",
                "python": "Python (main.py)",
                "web": "HTML, CSS y JavaScript",
            }[language]
            raise EvaluatorValidationError(f"Solo se permiten los archivos de {expected} en esta actividad.")
        if not isinstance(raw_content, str):
            raise EvaluatorValidationError(f"El contenido de {raw_name} debe ser texto.")
        size = len(raw_content.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            raise EvaluatorValidationError(f"El archivo {raw_name} supera el límite de 256 KiB.")
        total += size
        normalised[name] = raw_content
    if total > MAX_TOTAL_BYTES:
        raise EvaluatorValidationError("El conjunto de archivos supera el límite de 1 MiB.")
    return normalised


def _definition_for(test_case: Any) -> tuple[str, str, dict[str, Any], Decimal, str]:
    if isinstance(test_case, dict):
        name = test_case.get("name", "test")
        test_type = test_case.get("type")
        definition = test_case.get("definition", test_case.get("config", {}))
        points = test_case.get("points", 0)
        feedback = test_case.get("feedback", "")
    else:
        name = test_case.name
        test_type = test_case.type
        definition = test_case.definition
        points = test_case.points
        feedback = test_case.feedback
    if not isinstance(name, str) or not name or len(name) > 160:
        raise EvaluatorValidationError("El nombre del test no es válido.")
    if not isinstance(test_type, str) or test_type not in SUPPORTED_TYPES:
        raise EvaluatorValidationError(f"Tipo de test no permitido: {test_type!r}.")
    if not isinstance(definition, dict):
        raise EvaluatorValidationError(f"La definición del test {name!r} debe ser un objeto.")
    missing = _REQUIRED[test_type] - set(definition)
    if missing:
        raise EvaluatorValidationError(f"Faltan campos en {name!r}: {', '.join(sorted(missing))}.")
    unknown = set(definition) - _OPTIONAL_BY_TYPE[test_type]
    if unknown:
        raise EvaluatorValidationError(f"Campos desconocidos en {name!r}: {', '.join(sorted(unknown))}.")
    for key, value in definition.items():
        if key in {
            "selector",
            "attribute",
            "first",
            "second",
            "query",
            "property",
            "name",
            "event",
            "target",
            "api",
            "command",
            "kind",
            "interpreter",
            "module",
            "mode",
            "encoding",
        }:
            if not isinstance(value, str) or not value or len(value) > MAX_SELECTOR_LENGTH:
                raise EvaluatorValidationError(f"El campo {key} de {name!r} no es válido.")
    if "expected" in definition and not isinstance(definition["expected"], (str, int, float, bool)):
        raise EvaluatorValidationError(f"El campo expected de {name!r} no es válido.")
    if test_type == "bash.shebang" and "expected" in definition and not isinstance(definition["expected"], str):
        raise EvaluatorValidationError(f"El campo expected de {name!r} debe ser texto.")
    if test_type == "bash.shebang" and "interpreter" in definition and not isinstance(definition["interpreter"], str):
        raise EvaluatorValidationError(f"El campo interpreter de {name!r} debe ser texto.")
    if test_type == "bash.shebang" and {"expected", "interpreter"}.issubset(definition):
        raise EvaluatorValidationError(f"El test {name!r} no puede indicar expected e interpreter a la vez.")
    if test_type == "bash.command_used":
        args = definition.get("args", [])
        if not isinstance(args, list) or len(args) > 32 or any(not isinstance(arg, str) or len(arg) > MAX_SELECTOR_LENGTH for arg in args):
            raise EvaluatorValidationError(f"Los argumentos de {name!r} no son válidos.")
    if test_type == "bash.node_kind":
        if definition["kind"].lower() not in BASH_NODE_KIND_ALIASES:
            raise EvaluatorValidationError(f"El tipo de nodo Bash de {name!r} no está permitido.")
    if test_type in {"python.assignment", "python.variable_assigned", "python.function_declared"}:
        candidate = definition["name"]
        if not candidate.isidentifier():
            raise EvaluatorValidationError(f"El nombre Python de {name!r} no es un identificador válido.")
    if test_type == "python.function_declared":
        if "args" in definition:
            args = definition["args"]
            if not isinstance(args, list) or len(args) > 32 or any(
                not isinstance(argument, str) or not argument.isidentifier() for argument in args
            ):
                raise EvaluatorValidationError(f"Los argumentos de {name!r} no son válidos.")
        if "returns" in definition and not isinstance(definition["returns"], bool):
            raise EvaluatorValidationError(f"El campo returns de {name!r} debe ser booleano.")
    if test_type == "python.node_kind":
        if definition["kind"].lower() not in PYTHON_NODE_KIND_ALIASES:
            raise EvaluatorValidationError(f"El tipo de nodo Python de {name!r} no está permitido.")
        if "non_empty" in definition and not isinstance(definition["non_empty"], bool):
            raise EvaluatorValidationError(f"El campo non_empty de {name!r} debe ser booleano.")
    if test_type == "python.call_used":
        candidate = definition["name"]
        if any(not part.isidentifier() for part in candidate.split(".")):
            raise EvaluatorValidationError(f"El nombre de llamada Python de {name!r} no es válido.")
        if "args" in definition:
            args = definition["args"]
            if not isinstance(args, list) or len(args) > 16 or any(not isinstance(arg, str) or len(arg) > MAX_SELECTOR_LENGTH for arg in args):
                raise EvaluatorValidationError(f"Los argumentos de {name!r} no son válidos.")
        if "arg_names" in definition:
            arg_names = definition["arg_names"]
            if not isinstance(arg_names, list) or len(arg_names) > 16 or any(
                not isinstance(argument, str)
                or any(not part.isidentifier() for part in argument.split("."))
                for argument in arg_names
            ):
                raise EvaluatorValidationError(f"Los nombres de argumento de {name!r} no son válidos.")
    if test_type == "python.import_used":
        module = definition["module"]
        if any(not part.isidentifier() for part in module.split(".")):
            raise EvaluatorValidationError(f"El módulo Python de {name!r} no es válido.")
    if test_type == "python.file_opened":
        if "mode" in definition and (
            not isinstance(definition["mode"], str) or definition["mode"] not in PYTHON_MODES
        ):
            raise EvaluatorValidationError(f"El modo de apertura de {name!r} no es válido.")
        if "context_manager" in definition and not isinstance(definition["context_manager"], bool):
            raise EvaluatorValidationError(f"context_manager de {name!r} debe ser booleano.")
        if "body_non_empty" in definition and not isinstance(definition["body_non_empty"], bool):
            raise EvaluatorValidationError(f"body_non_empty de {name!r} debe ser booleano.")
        if "encoding" in definition and any(char in definition["encoding"] for char in "\r\n"):
            raise EvaluatorValidationError(f"La codificación de {name!r} no es válida.")
    if test_type == "python.attribute_used":
        candidate = definition["name"]
        if "." not in candidate or any(not part.isidentifier() for part in candidate.split(".")):
            raise EvaluatorValidationError(f"El nombre de atributo Python de {name!r} no es válido.")
    if test_type == "python.subscript_used":
        candidate = definition["name"]
        if any(not part.isidentifier() for part in candidate.split(".")):
            raise EvaluatorValidationError(f"El destino subscriptado de {name!r} no es válido.")
        key = definition["key"]
        if not isinstance(key, str) or not key or len(key) > MAX_SELECTOR_LENGTH:
            raise EvaluatorValidationError(f"La clave subscriptada de {name!r} no es válida.")
    if test_type == "python.dict_keys":
        candidate = definition["name"]
        if not candidate.isidentifier():
            raise EvaluatorValidationError(f"El nombre del diccionario de {name!r} no es válido.")
        keys = definition["keys"]
        if not isinstance(keys, list) or len(keys) > 32 or any(
            not isinstance(key, str) or not key or len(key) > MAX_SELECTOR_LENGTH for key in keys
        ):
            raise EvaluatorValidationError(f"Las claves del diccionario de {name!r} no son válidas.")
    if test_type == "python.loop_target":
        candidate = definition["name"]
        if not candidate.isidentifier():
            raise EvaluatorValidationError(f"El destino del bucle de {name!r} no es válido.")
        if "iterable" in definition:
            iterable = definition["iterable"]
            if not isinstance(iterable, str) or any(not part.isidentifier() for part in iterable.split(".")):
                raise EvaluatorValidationError(f"El iterable del bucle de {name!r} no es válido.")
    if test_type == "python.exception_handled":
        candidate = definition["name"]
        if any(not part.isidentifier() for part in candidate.split(".")):
            raise EvaluatorValidationError(f"La excepción de {name!r} no es válida.")
    if test_type == "python.comparison_used":
        operator = definition["operator"]
        if not isinstance(operator, str) or operator not in PYTHON_COMPARISON_ALIASES:
            raise EvaluatorValidationError(f"El operador de comparación de {name!r} no es válido.")
        if "left" in definition:
            left = definition["left"]
            if not isinstance(left, str) or any(not part.isidentifier() for part in left.split(".")):
                raise EvaluatorValidationError(f"El operando izquierdo de {name!r} no es válido.")
        if "right" in definition and not isinstance(definition["right"], (str, int, float, bool)):
            raise EvaluatorValidationError(f"El operando derecho de {name!r} no es válido.")
    if test_type == "html.selector_count":
        expected = definition["expected"]
        if not isinstance(expected, int) or expected < 0 or expected > MAX_NODES:
            raise EvaluatorValidationError(f"El recuento esperado de {name!r} no es válido.")
    try:
        points_decimal = Decimal(str(points))
    except (InvalidOperation, TypeError):
        raise EvaluatorValidationError(f"Los puntos de {name!r} no son válidos.") from None
    if not points_decimal.is_finite() or points_decimal < 0 or points_decimal > Decimal("10000"):
        raise EvaluatorValidationError(f"Los puntos de {name!r} no son válidos.")
    return name, test_type, definition, points_decimal, feedback if isinstance(feedback, str) else ""


def validate_test_definition(test_type: str, definition: dict[str, Any], *, points: Any = 1) -> None:
    """Validate a DSL test before a teacher can publish its activity version."""

    _definition_for({"name": "validation", "type": test_type, "definition": definition, "points": points})


def _parse_html(html: str):
    soup = BeautifulSoup(html, "html5lib")
    if len(list(soup.descendants)) > MAX_NODES:
        raise EvaluatorValidationError("El HTML contiene demasiados nodos.")
    return soup


def _normalise_css(value: str) -> str:
    return " ".join(value.split())


def _parse_css(css: str):
    rules = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    if any(getattr(rule, "type", None) == "error" for rule in rules):
        # A malformed stylesheet is a student failure for CSS assertions, not
        # an evaluator failure.
        return rules, True
    return rules, False


def _css_rules(rules: Iterable[Any]):
    for rule in rules:
        if getattr(rule, "type", None) == "qualified-rule":
            selector = _normalise_css(tinycss2.serialize(rule.prelude).strip())
            declarations = tinycss2.parse_declaration_list(rule.content, skip_whitespace=True, skip_comments=True)
            yield selector, declarations


def _parse_js(javascript: str):
    try:
        return esprima.parseScript(javascript, tolerant=False), None
    except Exception as exc:  # esprima raises several parser-specific classes
        return None, str(exc)


def _walk(node: Any):
    if node is None:
        return
    if isinstance(node, list):
        for item in node:
            yield from _walk(item)
        return
    if not hasattr(node, "type"):
        return
    yield node
    for key, value in vars(node).items():
        if key.startswith("_"):
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                yield from _walk(item)
        elif hasattr(value, "type"):
            yield from _walk(value)


def _identifier_name(node: Any) -> str | None:
    return getattr(node, "name", None) if getattr(node, "type", None) == "Identifier" else None


def _member_chain(node: Any) -> str | None:
    if getattr(node, "type", None) == "Identifier":
        return node.name
    if getattr(node, "type", None) != "MemberExpression":
        return None
    left = _member_chain(getattr(node, "object", None))
    if getattr(node, "computed", False):
        prop = getattr(getattr(node, "property", None), "value", None)
    else:
        prop = _identifier_name(getattr(node, "property", None))
    if left and isinstance(prop, str):
        return f"{left}.{prop}"
    return None


@dataclass(frozen=True)
class BashAnalysis:
    """One immutable parse result shared by every Bash test in a run."""

    source: str
    source_bytes: bytes
    root: Any
    nodes: tuple[Any, ...]
    syntax_error: str | None = None


def _bash_node_text(node: Any, source: str | bytes) -> str:
    source_bytes = source if isinstance(source, bytes) else source.encode("utf-8")
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _bash_error_message(root: Any, source: str) -> str:
    """Return a short, non-source-leaking syntax diagnostic."""

    stack = [root]
    while stack:
        node = stack.pop()
        if getattr(node, "is_error", False) or getattr(node, "is_missing", False) or node.type == "ERROR":
            row, _column = node.start_point
            return f"Sintaxis Bash no válida cerca de la línea {row + 1}."
        stack.extend(reversed(node.children))
    return "La sintaxis Bash no es válida."


def _parse_bash(source: str) -> BashAnalysis:
    """Parse Bash once and enforce resource limits without invoking a shell."""

    parser = Parser(Language(tree_sitter_bash.language()))
    source_bytes = source.encode("utf-8")
    try:
        tree = parser.parse(source_bytes)
    except (MemoryError, RecursionError) as exc:
        raise EvaluatorValidationError("El script Bash es demasiado complejo para analizarlo.") from exc
    root = tree.root_node
    nodes: list[Any] = []
    stack = [(root, 0)]
    max_depth = 0
    while stack:
        node, depth = stack.pop()
        nodes.append(node)
        max_depth = max(max_depth, depth)
        if len(nodes) > MAX_BASH_NODES:
            raise EvaluatorValidationError("El script Bash contiene demasiados nodos.")
        if depth > MAX_BASH_DEPTH:
            raise EvaluatorValidationError("El script Bash tiene una anidación excesiva.")
        stack.extend((child, depth + 1) for child in reversed(node.children))
    syntax_error = _bash_error_message(root, source) if root.has_error else None
    return BashAnalysis(source, source_bytes, root, tuple(nodes), syntax_error)


def _bash_literal(value: str) -> str:
    """Compare literal shell tokens without expanding or interpreting them."""

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _bash_command_tokens(node: Any, source: str, source_bytes: bytes | None = None) -> tuple[str, list[str]] | None:
    if node.type != "command":
        return None
    command_name = node.child_by_field_name("name")
    if command_name is None:
        return None
    source_value = source_bytes if source_bytes is not None else source
    name = _bash_literal(_bash_node_text(command_name, source_value))
    arguments: list[str] = []
    for child in node.named_children:
        if child == command_name or child.type in {"command_name", "variable_assignment", "file_redirect", "heredoc_redirect", "redirect"}:
            continue
        arguments.append(_bash_literal(_bash_node_text(child, source_value)))
    return name, arguments


def _bash_command_used(analysis: BashAnalysis, definition: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected_command = definition["command"]
    expected_args = definition.get("args")
    matches = []
    for node in analysis.nodes:
        tokens = _bash_command_tokens(node, analysis.source, analysis.source_bytes)
        if not tokens:
            continue
        command, arguments = tokens
        if command != expected_command:
            continue
        if expected_args is not None and arguments != expected_args:
            continue
        matches.append(arguments)
    return bool(matches), {"command": expected_command, "matches": len(matches)}


def _bash_variable_assigned(analysis: BashAnalysis, name: str) -> tuple[bool, dict[str, Any]]:
    found = False
    for node in analysis.nodes:
        variable = node.child_by_field_name("name") if node.type == "variable_assignment" else None
        if node.type == "for_statement":
            # A for loop's variable_name is an assignment/binding even though
            # the Bash grammar does not call it variable_assignment.
            variable = next((child for child in node.named_children if child.type == "variable_name"), None)
        if variable is not None and _bash_node_text(variable, analysis.source_bytes) == name:
            found = True
            break
    return found, {"name": name}


def _run_bash_test(test_type: str, definition: dict[str, Any], analysis: BashAnalysis) -> tuple[bool, dict[str, Any]]:
    if test_type == "bash.syntax_valid":
        return analysis.syntax_error is None, {"error": analysis.syntax_error or ""}
    if test_type == "bash.shebang":
        first_line = analysis.source.splitlines()[0] if analysis.source.splitlines() else ""
        if not first_line.startswith("#!"):
            return False, {"present": False}
        expected = definition.get("expected")
        interpreter = definition.get("interpreter")
        if expected is not None:
            expected_line = expected if expected.startswith("#!") else f"#!{expected}"
            return first_line == expected_line, {"present": True, "expected": expected_line}
        if interpreter is not None:
            return first_line[2:].strip().split()[-1:] == [interpreter], {"present": True, "interpreter": interpreter}
        return True, {"present": True}
    if analysis.syntax_error is not None:
        return False, {"error": "El script Bash no tiene una sintaxis válida."}
    if test_type == "bash.command_used":
        return _bash_command_used(analysis, definition)
    if test_type == "bash.variable_assigned":
        return _bash_variable_assigned(analysis, definition["name"])
    if test_type == "bash.node_kind":
        expected_kind = BASH_NODE_KIND_ALIASES[definition["kind"].lower()]
        count = sum(1 for node in analysis.nodes if node.type == expected_kind)
        return count > 0, {"kind": expected_kind, "count": count}
    raise EvaluatorValidationError(f"Tipo de test Bash no implementado: {test_type}")


@dataclass(frozen=True)
class PythonAnalysis:
    """One immutable AST parse shared by all Python tests in one run.

    The AST is data only.  Nothing in this class imports modules, resolves
    names, reads paths or invokes a Python callable from the submitted text.
    """

    source: str
    root: ast.AST | None
    nodes: tuple[ast.AST, ...]
    syntax_error: str | None = None
    context_call_ids: frozenset[int] = frozenset()
    context_non_empty_call_ids: frozenset[int] = frozenset()
    pathlib_module_aliases: frozenset[str] = frozenset()
    pathlib_constructor_aliases: frozenset[str] = frozenset()
    pathlib_path_variables: frozenset[str] = frozenset()
    bare_open_shadowed: bool = False


def _python_syntax_message(exc: SyntaxError) -> str:
    line = getattr(exc, "lineno", None)
    if isinstance(line, int) and line > 0:
        return f"Sintaxis Python no válida cerca de la línea {line}."
    return "La sintaxis Python no es válida."


def _parse_python(source: str) -> PythonAnalysis:
    """Parse Python source once, without executing it."""

    try:
        root = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        return PythonAnalysis(source, None, (), _python_syntax_message(exc))
    except (ValueError, TypeError):
        # NUL bytes and malformed parser input are student syntax failures,
        # not evaluator crashes.  Keep the diagnostic source-independent.
        return PythonAnalysis(source, None, (), "El texto Python no se puede analizar.")
    except (MemoryError, RecursionError) as exc:
        raise EvaluatorValidationError("El programa Python es demasiado complejo para analizarlo.") from exc

    nodes: list[ast.AST] = []
    stack: list[tuple[ast.AST, int]] = [(root, 0)]
    max_depth = 0
    while stack:
        node, depth = stack.pop()
        nodes.append(node)
        if len(nodes) > MAX_PYTHON_NODES:
            raise EvaluatorValidationError("El programa Python contiene demasiados nodos.")
        max_depth = max(max_depth, depth)
        if max_depth > MAX_PYTHON_DEPTH:
            raise EvaluatorValidationError("El programa Python tiene una anidación excesiva.")
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))

    context_call_ids: set[int] = set()
    context_non_empty_call_ids: set[int] = set()
    for node in nodes:
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            # Only the direct context expression is a resource manager.  A
            # nested call such as ``with wrapper(open(...))`` does not prove
            # that the inner call itself is managed by ``with``.
            if isinstance(item.context_expr, ast.Call):
                context_call_ids.add(id(item.context_expr))
                if any(not isinstance(statement, ast.Pass) for statement in node.body):
                    context_non_empty_call_ids.add(id(item.context_expr))
    pathlib_module_aliases, pathlib_constructor_aliases, pathlib_path_variables = _python_path_symbols(nodes)
    return PythonAnalysis(
        source,
        root,
        tuple(nodes),
        context_call_ids=frozenset(context_call_ids),
        context_non_empty_call_ids=frozenset(context_non_empty_call_ids),
        pathlib_module_aliases=pathlib_module_aliases,
        pathlib_constructor_aliases=pathlib_constructor_aliases,
        pathlib_path_variables=pathlib_path_variables,
        bare_open_shadowed=_python_open_is_shadowed(nodes),
    )


def _python_dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _python_dotted_name(node.value)
        if left is None and isinstance(node.value, ast.Call):
            # Keep useful class-qualified names for expressions such as
            # ``Path("datos.txt").open()`` without resolving the call.
            left = _python_dotted_name(node.value.func)
        return f"{left}.{node.attr}" if left else None
    return None


def _python_target_names(node: ast.AST | None):
    if node is None:
        return
    if isinstance(node, ast.Name):
        yield node.id
        return
    if isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            yield from _python_target_names(element)
        return
    if isinstance(node, ast.Starred):
        yield from _python_target_names(node.value)


def _python_open_is_shadowed(nodes: Iterable[ast.AST]) -> bool:
    """Conservatively detect bindings that make bare ``open`` ambiguous.

    The evaluator must not resolve or execute names.  Rejecting a bare call
    whenever the source binds ``open`` avoids treating a teacher-defined
    helper, parameter or imported symbol as the built-in file function.  A
    deliberate ``from builtins import open`` remains unambiguous.
    """

    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == "open":
            return True
        if isinstance(node, ast.arg) and node.arg == "open":
            return True
        if isinstance(node, ast.Name) and node.id == "open" and isinstance(node.ctx, (ast.Store, ast.Del)):
            return True
        if isinstance(node, ast.ExceptHandler) and node.name == "open":
            return True
        if isinstance(node, ast.MatchAs) and node.name == "open":
            return True
        if isinstance(node, ast.MatchStar) and node.name == "open":
            return True
        if isinstance(node, ast.MatchMapping) and node.rest == "open":
            return True
        if isinstance(node, ast.Import):
            if any((alias.asname or alias.name.split(".", 1)[0]) == "open" for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if any(
                (alias.asname or alias.name) == "open"
                and not (node.module == "builtins" and alias.name == "open")
                for alias in node.names
            ):
                return True
    return False


def _python_is_path_constructor_call(
    node: ast.AST | None,
    pathlib_module_aliases: frozenset[str] | set[str],
    pathlib_constructor_aliases: frozenset[str] | set[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    constructor = _python_dotted_name(node.func)
    if constructor in pathlib_constructor_aliases:
        return True
    return any(
        constructor == f"{module}.{path_type}"
        for module in pathlib_module_aliases
        for path_type in ("Path", "PurePath")
    )


def _python_path_symbols(nodes: Iterable[ast.AST]) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Collect only syntactically imported pathlib constructors and instances."""

    pathlib_module_aliases: set[str] = set()
    pathlib_constructor_aliases: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pathlib":
                    pathlib_module_aliases.add(alias.asname or "pathlib")
        elif isinstance(node, ast.ImportFrom) and node.module == "pathlib":
            for alias in node.names:
                if alias.name in {"Path", "PurePath"}:
                    pathlib_constructor_aliases.add(alias.asname or alias.name)

    pathlib_path_variables: set[str] = set()
    for node in nodes:
        targets: list[ast.AST] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
            value = node.value
        elif isinstance(node, ast.NamedExpr):
            targets.append(node.target)
            value = node.value
        if value is None or not _python_is_path_constructor_call(
            value, pathlib_module_aliases, pathlib_constructor_aliases
        ):
            continue
        for target in targets:
            pathlib_path_variables.update(_python_target_names(target))
    return (
        frozenset(pathlib_module_aliases),
        frozenset(pathlib_constructor_aliases),
        frozenset(pathlib_path_variables),
    )


def _python_is_path_receiver(receiver: ast.AST, analysis: PythonAnalysis) -> bool:
    if isinstance(receiver, ast.Name):
        return receiver.id in analysis.pathlib_path_variables
    return _python_is_path_constructor_call(
        receiver,
        analysis.pathlib_module_aliases,
        analysis.pathlib_constructor_aliases,
    )


def _python_assignment(analysis: PythonAnalysis, name: str) -> tuple[bool, dict[str, Any]]:
    found = False
    for node in analysis.nodes:
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets.append(node.target)
        elif isinstance(node, ast.NamedExpr):
            targets.append(node.target)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets.append(node.target)
        elif isinstance(node, (ast.comprehension,)):
            targets.append(node.target)
        elif isinstance(node, ast.withitem):
            targets.append(node.optional_vars)
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
            if node.name == name:
                found = True
                break
        if any(name == target_name for target in targets for target_name in _python_target_names(target)):
            found = True
            break
    return found, {"name": name}


def _python_call_literal_args(node: ast.Call) -> list[str] | None:
    """Return stringified literal positional args, or None for dynamic args."""

    values: list[str] = []
    for argument in node.args:
        if isinstance(argument, ast.Constant) and isinstance(argument.value, (str, int, float, bool)):
            values.append(str(argument.value))
        else:
            return None
    return values


def _python_call_argument_names(node: ast.Call) -> list[str] | None:
    """Return dotted names used as positional arguments, without resolving them."""

    values: list[str] = []
    for argument in node.args:
        dotted_name = _python_dotted_name(argument)
        if dotted_name is None:
            return None
        values.append(dotted_name)
    return values


def _python_open_calls(analysis: PythonAnalysis):
    for node in analysis.nodes:
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            is_open = node.func.id == "open" and not analysis.bare_open_shadowed
            mode_index = 1
            encoding_index = 3
        elif isinstance(node.func, ast.Attribute):
            is_open = node.func.attr == "open" and _python_is_path_receiver(node.func.value, analysis)
            mode_index = 0
            encoding_index = 2
        else:
            is_open = False
            mode_index = 0
            encoding_index = 0
        if not is_open:
            continue
        mode: str | None = "r"  # open() defaults to text read mode.
        encoding = None
        if len(node.args) > mode_index:
            mode = (
                node.args[mode_index].value
                if isinstance(node.args[mode_index], ast.Constant) and isinstance(node.args[mode_index].value, str)
                else None
            )
        if len(node.args) > encoding_index:
            encoding = (
                node.args[encoding_index].value
                if isinstance(node.args[encoding_index], ast.Constant) and isinstance(node.args[encoding_index].value, str)
                else None
            )
        for keyword in node.keywords:
            if keyword.arg == "mode":
                mode = (
                    keyword.value.value
                    if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str)
                    else None
                )
            elif keyword.arg == "encoding":
                encoding = (
                    keyword.value.value
                    if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str)
                    else None
                )
        yield node, mode, encoding, id(node) in analysis.context_call_ids


def _python_literal_value(node: ast.AST | None):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
        return node.value
    return None


def _python_file_opened(analysis: PythonAnalysis, definition: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected_mode = definition.get("mode")
    expected_context = definition.get("context_manager")
    expected_encoding = definition.get("encoding")
    expected_non_empty = definition.get("body_non_empty")
    matches = []
    for node, mode, encoding, in_context in _python_open_calls(analysis):
        if expected_mode is not None and mode != expected_mode:
            continue
        if expected_context is not None and in_context != expected_context:
            continue
        if expected_encoding is not None and encoding != expected_encoding:
            continue
        if expected_non_empty is not None and (
            (id(node) in analysis.context_non_empty_call_ids) != expected_non_empty
        ):
            continue
        matches.append({"mode": mode, "encoding": encoding, "context_manager": in_context})
    return bool(matches), {
        "matches": len(matches),
        "mode": expected_mode or "",
        "context_manager": expected_context,
        "encoding": expected_encoding or "",
        "body_non_empty": expected_non_empty,
    }


def _python_import_used(analysis: PythonAnalysis, module: str) -> tuple[bool, dict[str, Any]]:
    found = False
    for node in analysis.nodes:
        if isinstance(node, ast.Import):
            found = any(alias.name == module for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_module = node.module or ""
            found = imported_module == module or any(
                f"{imported_module}.{alias.name}" == module for alias in node.names
            )
        if found:
            break
    return found, {"module": module}


def _python_block_non_empty(node: ast.AST) -> bool:
    body = getattr(node, "body", None)
    return isinstance(body, list) and any(not isinstance(statement, ast.Pass) for statement in body)


def _python_node_kind_matches(node: ast.AST, expected_kind: str, non_empty: bool = False) -> bool:
    if expected_kind == "__if_else__":
        matches = isinstance(node, ast.If) and bool(node.orelse)
    else:
        matches = type(node).__name__ == expected_kind
    return matches and (not non_empty or _python_block_non_empty(node))


def _python_function_has_return(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    stack: list[ast.AST] = list(function.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))
    return False


def _python_attribute_used(analysis: PythonAnalysis, expected_name: str) -> tuple[bool, dict[str, Any]]:
    found = any(
        isinstance(node, ast.Attribute) and _python_dotted_name(node) == expected_name
        for node in analysis.nodes
    )
    return found, {"name": expected_name}


def _python_subscript_used(
    analysis: PythonAnalysis, expected_name: str, expected_key: str
) -> tuple[bool, dict[str, Any]]:
    found = any(
        isinstance(node, ast.Subscript)
        and _python_dotted_name(node.value) == expected_name
        and _python_literal_value(node.slice) == expected_key
        for node in analysis.nodes
    )
    return found, {"name": expected_name, "key": expected_key}


def _python_dict_keys(
    analysis: PythonAnalysis, expected_name: str, expected_keys: list[str]
) -> tuple[bool, dict[str, Any]]:
    found = False
    for node in analysis.nodes:
        targets: list[ast.AST] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
            value = node.value
        elif isinstance(node, ast.NamedExpr):
            targets.append(node.target)
            value = node.value
        if value is None or not isinstance(value, ast.Dict):
            continue
        assigned = any(expected_name == target_name for target in targets for target_name in _python_target_names(target))
        if not assigned:
            continue
        literal_keys = {
            key.value for key in value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        found = all(key in literal_keys for key in expected_keys)
        if found:
            break
    return found, {"name": expected_name, "keys": expected_keys}


def _python_loop_target(
    analysis: PythonAnalysis, expected_name: str, expected_iterable: str | None
) -> tuple[bool, dict[str, Any]]:
    found = False
    for node in analysis.nodes:
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        if expected_name not in set(_python_target_names(node.target)):
            continue
        if expected_iterable is not None and _python_dotted_name(node.iter) != expected_iterable:
            continue
        found = True
        break
    return found, {"name": expected_name, "iterable": expected_iterable or ""}


def _python_exception_handled(analysis: PythonAnalysis, expected_name: str) -> tuple[bool, dict[str, Any]]:
    found = any(
        isinstance(node, ast.ExceptHandler)
        and node.type is not None
        and _python_dotted_name(node.type) == expected_name
        for node in analysis.nodes
    )
    return found, {"name": expected_name}


def _python_comparison_used(
    analysis: PythonAnalysis,
    expected_operator: str,
    expected_left: str | None,
    expected_right: Any,
) -> tuple[bool, dict[str, Any]]:
    expected_ast_operator = PYTHON_COMPARISON_ALIASES[expected_operator]
    found = False
    for node in analysis.nodes:
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        for operator, comparator in zip(node.ops, node.comparators, strict=True):
            if type(operator).__name__ != expected_ast_operator:
                left = comparator
                continue
            if expected_left is not None and _python_dotted_name(left) != expected_left:
                left = comparator
                continue
            if expected_right is not None and _python_literal_value(comparator) != expected_right:
                left = comparator
                continue
            found = True
            break
        if found:
            break
    return found, {
        "operator": expected_operator,
        "left": expected_left or "",
        "right": expected_right,
    }


def _run_python_test(test_type: str, definition: dict[str, Any], analysis: PythonAnalysis) -> tuple[bool, dict[str, Any]]:
    if test_type == "python.syntax_valid":
        return analysis.syntax_error is None, {"error": analysis.syntax_error or ""}
    if analysis.syntax_error is not None:
        return False, {"error": "El Python no tiene una sintaxis válida."}
    if test_type in {"python.assignment", "python.variable_assigned"}:
        return _python_assignment(analysis, definition["name"])
    if test_type == "python.function_declared":
        name = definition["name"]
        found = False
        for node in analysis.nodes:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != name:
                continue
            if "args" in definition:
                actual_args = [
                    argument.arg
                    for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
                ]
                if actual_args != definition["args"]:
                    continue
            if "returns" in definition and _python_function_has_return(node) != definition["returns"]:
                continue
            found = True
            break
        return found, {"name": name}
    if test_type == "python.node_kind":
        expected_kind = PYTHON_NODE_KIND_ALIASES[definition["kind"].lower()]
        non_empty = definition.get("non_empty", False)
        count = sum(
            1 for node in analysis.nodes if _python_node_kind_matches(node, expected_kind, non_empty=non_empty)
        )
        return count > 0, {"kind": expected_kind, "count": count, "non_empty": non_empty}
    if test_type == "python.call_used":
        expected_name = definition["name"]
        expected_args = definition.get("args")
        expected_arg_names = definition.get("arg_names")
        matches = []
        for node in analysis.nodes:
            if not isinstance(node, ast.Call) or _python_dotted_name(node.func) != expected_name:
                continue
            if expected_args is not None and _python_call_literal_args(node) != expected_args:
                continue
            if expected_arg_names is not None and _python_call_argument_names(node) != expected_arg_names:
                continue
            matches.append(node)
        return bool(matches), {"name": expected_name, "matches": len(matches)}
    if test_type == "python.import_used":
        return _python_import_used(analysis, definition["module"])
    if test_type == "python.file_opened":
        return _python_file_opened(analysis, definition)
    if test_type == "python.attribute_used":
        return _python_attribute_used(analysis, definition["name"])
    if test_type == "python.subscript_used":
        return _python_subscript_used(analysis, definition["name"], definition["key"])
    if test_type == "python.dict_keys":
        return _python_dict_keys(analysis, definition["name"], definition["keys"])
    if test_type == "python.loop_target":
        return _python_loop_target(analysis, definition["name"], definition.get("iterable"))
    if test_type == "python.exception_handled":
        return _python_exception_handled(analysis, definition["name"])
    if test_type == "python.comparison_used":
        return _python_comparison_used(
            analysis,
            definition["operator"],
            definition.get("left"),
            definition.get("right"),
        )
    raise EvaluatorValidationError(f"Tipo de test Python no implementado: {test_type}")


def _run_test(
    test_type: str,
    definition: dict[str, Any],
    files: dict[str, str],
    *,
    bash_analysis: BashAnalysis | None = None,
    python_analysis: PythonAnalysis | None = None,
) -> tuple[bool, dict[str, Any]]:
    if test_type.startswith("bash."):
        if bash_analysis is None:
            bash_analysis = _parse_bash(files["bash"])
        return _run_bash_test(test_type, definition, bash_analysis)
    if test_type.startswith("python."):
        if python_analysis is None:
            python_analysis = _parse_python(files["python"])
        return _run_python_test(test_type, definition, python_analysis)
    if test_type.startswith("html."):
        soup = _parse_html(files["html"])
        selector = definition.get("selector")
        if test_type == "html.selector_exists":
            matches = soup.select(selector)
            return bool(matches), {"count": len(matches)}
        if test_type == "html.selector_count":
            matches = soup.select(selector)
            return len(matches) == definition["expected"], {"count": len(matches), "expected": definition["expected"]}
        if test_type == "html.text_contains":
            matches = soup.select(selector)
            expected = str(definition["expected"])
            ok = any(expected in match.get_text(" ", strip=True) for match in matches)
            return ok, {"matches": len(matches), "expected": expected}
        if test_type == "html.attribute_equals":
            matches = soup.select(selector)
            expected = str(definition["expected"])
            ok = any(match.get(definition["attribute"]) == expected for match in matches)
            return ok, {"matches": len(matches), "attribute": definition["attribute"]}
        if test_type == "html.forbidden_element_absent":
            matches = soup.select(selector)
            return not matches, {"count": len(matches)}
        first = soup.select(definition["first"])
        second = soup.select(definition["second"])
        if not first or not second:
            return False, {"first_count": len(first), "second_count": len(second)}
        all_elements = list(soup.find_all())
        return all_elements.index(first[0]) < all_elements.index(second[0]), {"first_count": len(first), "second_count": len(second)}

    if test_type.startswith("css."):
        rules, malformed = _parse_css(files["css"])
        if test_type == "css.media_query_exists":
            expected = _normalise_css(definition["query"])
            found = [rule for rule in rules if getattr(rule, "type", None) == "at-rule" and getattr(rule, "at_keyword", "").lower() == "media" and _normalise_css(tinycss2.serialize(rule.prelude).strip()) == expected]
            return bool(found), {"expected": expected}
        selector = _normalise_css(definition.get("selector", ""))
        matched = [(rule_selector, declarations) for rule_selector, declarations in _css_rules(rules) if rule_selector == selector]
        if test_type == "css.selector_exists":
            return bool(matched), {"matches": len(matched)}
        if test_type == "css.declaration_equals":
            property_name = definition["property"].lower()
            expected = _normalise_css(str(definition["expected"]))
            ok = any(any(getattr(decl, "type", None) == "declaration" and decl.name.lower() == property_name and _normalise_css(tinycss2.serialize(decl.value).strip()) == expected for decl in declarations) for _, declarations in matched)
            return ok and not malformed, {"matches": len(matched), "property": property_name}
        property_name = definition["property"].lower()
        found = any(getattr(decl, "type", None) == "declaration" and decl.name.lower() == property_name for _, declarations in _css_rules(rules) for decl in declarations)
        return (not found) and not malformed, {"property": property_name, "found": found}

    tree, syntax_error = _parse_js(files["javascript"])
    if test_type == "js.syntax_valid":
        return syntax_error is None, {"error": syntax_error or ""}
    if syntax_error is not None:
        return False, {"error": "El JavaScript no tiene una sintaxis válida."}
    nodes = list(_walk(tree))
    if len(nodes) > MAX_NODES:
        raise EvaluatorValidationError("El JavaScript contiene demasiados nodos.")
    if test_type == "js.function_declared":
        name = definition["name"]
        found = any(getattr(node, "type", None) == "FunctionDeclaration" and _identifier_name(getattr(node, "id", None)) == name for node in nodes)
        return found, {"name": name}
    if test_type == "js.variable_declared":
        name = definition["name"]
        found = any(getattr(node, "type", None) == "VariableDeclarator" and _identifier_name(getattr(node, "id", None)) == name for node in nodes)
        return found, {"name": name}
    if test_type == "js.event_listener_registered":
        event = definition["event"]
        target = definition.get("target")
        found = False
        for node in nodes:
            if getattr(node, "type", None) != "CallExpression":
                continue
            callee = getattr(node, "callee", None)
            if _member_chain(callee) not in {"addEventListener", "document.addEventListener", "window.addEventListener", "document.body.addEventListener", "body.addEventListener"} and not (_member_chain(callee) or "").endswith(".addEventListener"):
                continue
            args = getattr(node, "arguments", [])
            first = getattr(args[0], "value", None) if args else None
            receiver = _member_chain(getattr(callee, "object", None)) if callee is not None else None
            found = first == event and (not target or receiver == target)
            if found:
                break
        return found, {"event": event, "target": target or ""}
    if test_type == "js.forbidden_api_absent":
        forbidden = definition["api"]
        found = any(_member_chain(getattr(node, "callee", None)) == forbidden or _member_chain(node) == forbidden for node in nodes if getattr(node, "type", None) in {"CallExpression", "MemberExpression", "Identifier"})
        return not found, {"api": forbidden, "found": found}
    raise EvaluatorValidationError(f"Tipo no implementado: {test_type}")


def evaluate_tests(
    files: dict[str, Any],
    test_cases: Iterable[Any],
    *,
    public_only: bool = False,
    language: str | None = None,
) -> EvaluationReport:
    """Evaluate declarative tests and return deterministic Decimal scores.

    ``language`` is explicit in application calls.  The small inference
    fallback keeps direct evaluator use convenient while still rejecting
    mixed Bash/web file payloads.
    """

    if language is None:
        file_keys = set(files) if isinstance(files, dict) else set()
        if "bash" in file_keys and not (file_keys & (set(WEB_FILE_KEYS) | set(PYTHON_FILE_KEYS))):
            language = "bash"
        elif (file_keys & set(PYTHON_FILE_ALIASES)) and not (file_keys & (set(WEB_FILE_KEYS) | {"bash"})):
            language = "python"
        else:
            language = "web"
    normalised_files = _normalise_files(files, language=language)
    cases = list(test_cases)
    if len(cases) > MAX_TESTS:
        raise EvaluatorValidationError("Una versión no puede tener más de 200 tests.")
    bash_analysis = _parse_bash(normalised_files["bash"]) if language == "bash" else None
    python_analysis = _parse_python(normalised_files["python"]) if language == "python" else None
    results: list[EvaluationResult] = []
    try:
        for _index, case in enumerate(cases):
            if public_only and not isinstance(case, dict) and case.visibility != "public":
                continue
            if public_only and isinstance(case, dict) and case.get("visibility", "public") != "public":
                continue
            name, test_type, definition, points, feedback = _definition_for(case)
            if language == "bash" and not test_type.startswith("bash."):
                raise EvaluatorValidationError("Una actividad Bash solo puede utilizar tests Bash.")
            if language == "python" and not test_type.startswith("python."):
                raise EvaluatorValidationError("Una actividad Python solo puede utilizar tests Python.")
            if language == "web" and (test_type.startswith("bash.") or test_type.startswith("python.")):
                raise EvaluatorValidationError("Una actividad web no puede utilizar tests Bash o Python.")
            if language == "bash" and test_type.startswith("python."):
                raise EvaluatorValidationError("Una actividad Bash no puede utilizar tests Python.")
            try:
                passed, detail = _run_test(
                    test_type,
                    definition,
                    normalised_files,
                    bash_analysis=bash_analysis,
                    python_analysis=python_analysis,
                )
                status = "passed" if passed else "failed"
            except (EvaluatorValidationError, Exception) as exc:
                # Parser bugs or resource errors belong to the corrector and
                # must never be turned into a student zero.
                status = "infra_error"
                passed = False
                detail = {"error": "Error interno del evaluador."}
                feedback = feedback or str(exc)
            earned = points if passed else Decimal("0")
            results.append(EvaluationResult(name, test_type, passed, status, points, earned, feedback, detail))
    except EvaluatorValidationError:
        raise
    except Exception as exc:
        raise EvaluatorInfrastructureError("El evaluador no pudo completar la ejecución.") from exc

    total = sum((result.points for result in results), Decimal("0"))
    passed_points = sum((result.earned_points for result in results if result.status == "passed"), Decimal("0"))
    has_infra = any(result.status == "infra_error" for result in results)
    score = (Decimal("10") * passed_points / total) if total > 0 and not has_infra else None
    return EvaluationReport("infra_error" if has_infra else ("passed" if all(r.passed for r in results) else "failed"), score, passed_points, total, results)


def displayed_score(score: Decimal | None) -> Decimal | None:
    if score is None:
        return None
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
