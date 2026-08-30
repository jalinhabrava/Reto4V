"""Declarative, non-executing evaluator for the first AulaWeb milestone.

Student files are parsed as data.  The evaluator never imports, evaluates or
executes JavaScript or Bash and never renders student HTML in the Django
process.  Bash is inspected with tree-sitter's Bash grammar; no shell,
subprocess, network or filesystem access is available to submitted source.
Public browser tests may offer richer feedback in the isolated preview, but
only this static evaluator can contribute to an official MVP score.
"""

from __future__ import annotations

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
EVALUATOR_VERSION = "static-v2"

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
}
_OPTIONAL_BY_TYPE = {
    **{test_type: {"selector", "expected", "attribute", "first", "second", "query", "property", "name", "event", "target", "api"} for test_type in SUPPORTED_TYPES if not test_type.startswith("bash.")},
    "bash.syntax_valid": set(),
    "bash.shebang": {"expected", "interpreter"},
    "bash.command_used": {"command", "args"},
    "bash.variable_assigned": {"name"},
    "bash.node_kind": {"kind"},
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
    if language not in {"web", "bash"}:
        raise EvaluatorValidationError("El lenguaje de la actividad no es válido.")
    allowed_keys = set(BASH_FILE_KEYS if language == "bash" else WEB_FILE_KEYS)
    normalised: dict[str, str] = {key: "" for key in allowed_keys}
    total = 0
    for raw_name, raw_content in files.items():
        raw_key = str(raw_name).lower()
        if language == "bash":
            name = "bash" if raw_key == "bash" else None
        else:
            name = FILE_ALIASES.get(raw_key)
        if name is None or name not in allowed_keys:
            expected = "Bash" if language == "bash" else "HTML, CSS y JavaScript"
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
    if test_type not in SUPPORTED_TYPES:
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
        if key in {"selector", "attribute", "first", "second", "query", "property", "name", "event", "target", "api", "command", "kind", "interpreter"}:
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
    if test_type == "html.selector_count":
        expected = definition["expected"]
        if not isinstance(expected, int) or expected < 0 or expected > MAX_NODES:
            raise EvaluatorValidationError(f"El recuento esperado de {name!r} no es válido.")
    try:
        points_decimal = Decimal(str(points))
    except (InvalidOperation, TypeError):
        raise EvaluatorValidationError(f"Los puntos de {name!r} no son válidos.") from None
    if points_decimal < 0 or points_decimal > Decimal("10000"):
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


def _run_test(test_type: str, definition: dict[str, Any], files: dict[str, str], *, bash_analysis: BashAnalysis | None = None) -> tuple[bool, dict[str, Any]]:
    if test_type.startswith("bash."):
        if bash_analysis is None:
            bash_analysis = _parse_bash(files["bash"])
        return _run_bash_test(test_type, definition, bash_analysis)
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
        language = "bash" if isinstance(files, dict) and "bash" in files and not any(key in files for key in WEB_FILE_KEYS) else "web"
    normalised_files = _normalise_files(files, language=language)
    cases = list(test_cases)
    if len(cases) > MAX_TESTS:
        raise EvaluatorValidationError("Una versión no puede tener más de 200 tests.")
    bash_analysis = _parse_bash(normalised_files["bash"]) if language == "bash" else None
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
            if language == "web" and test_type.startswith("bash."):
                raise EvaluatorValidationError("Una actividad web no puede utilizar tests Bash.")
            try:
                passed, detail = _run_test(test_type, definition, normalised_files, bash_analysis=bash_analysis)
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
