from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from grading.evaluator import evaluate_tests, validate_test_definition


class JavaScriptEvaluatorTests(SimpleTestCase):
    def test_calls_literals_and_names_come_from_the_ast_not_comments_or_strings(self):
        source = """
const nombre = "Ada";
// console.log("Falso");
/* console.log("Tampoco"); */
const texto = "console.log('Tampoco')";
console.log(nombre);
console.log("Hola");
"""
        report = evaluate_tests(
            {"javascript": source},
            [
                {"name": "nombre", "type": "js.call_used", "definition": {"name": "console.log", "arg_names": ["nombre"]}, "points": 1},
                {"name": "saludo", "type": "js.call_used", "definition": {"name": "console.log", "args": ["Hola"]}, "points": 1},
                {"name": "falso", "type": "js.call_used", "definition": {"name": "console.log", "args": ["Falso"]}, "points": 1},
            ],
            language="web",
        )

        self.assertEqual(report.score, Decimal("6.666666666666666666666666667"))
        self.assertTrue(report.results[0].passed)
        self.assertTrue(report.results[1].passed)
        self.assertFalse(report.results[2].passed)

    def test_literal_variable_and_allowed_node_kinds_are_static(self):
        source = """
const cantidad = 3;
const productos = ["Lápiz"];
if (cantidad > 0) {
  for (const producto of productos) {
    console.log(producto);
  }
}
function duplicar(numero) {
  return numero * 2;
}
const total = cantidad * cantidad;
const estado = document.getElementById("estado");
estado.textContent = "Listo";
"""
        tests = [
            {"name": "literal", "type": "js.variable_declared", "definition": {"name": "cantidad", "expected": 3}, "points": 1},
            {"name": "lista", "type": "js.node_kind", "definition": {"kind": "array"}, "points": 1},
            {"name": "if", "type": "js.node_kind", "definition": {"kind": "if"}, "points": 1},
            {"name": "bucle", "type": "js.node_kind", "definition": {"kind": "for_of"}, "points": 1},
            {"name": "función", "type": "js.node_kind", "definition": {"kind": "function"}, "points": 1},
            {"name": "return", "type": "js.node_kind", "definition": {"kind": "return"}, "points": 1},
            {"name": "inicializador", "type": "js.variable_declared", "definition": {"name": "total", "operator": "*", "left": "cantidad", "right": "cantidad"}, "points": 1},
            {"name": "retorno exacto", "type": "js.return_expression", "definition": {"operator": "*", "left": "numero", "right": 2}, "points": 1},
            {"name": "asignación exacta", "type": "js.assignment_equals", "definition": {"target": "estado.textContent", "expected": "Listo"}, "points": 1},
        ]

        report = evaluate_tests({"javascript": source}, tests, language="web")

        self.assertEqual(report.status, "passed")
        self.assertEqual(report.score, Decimal("10"))
        not_literal = evaluate_tests(
            {"javascript": "let cantidad;\ncantidad = 3;\n"},
            [{"name": "literal", "type": "js.variable_declared", "definition": {"name": "cantidad", "expected": 3}, "points": 1}],
            language="web",
        )
        self.assertFalse(not_literal.results[0].passed)

    def test_source_is_parsed_once_and_never_executed(self):
        source = 'throw new Error("no se ejecuta");\nconsole.log("visible");\n'
        tests = [
            {"name": "sintaxis", "type": "js.syntax_valid", "definition": {}, "points": 1},
            {"name": "mensaje", "type": "js.call_used", "definition": {"name": "console.log", "args": ["visible"]}, "points": 1},
        ]
        from grading import evaluator

        with patch("grading.evaluator._parse_js", wraps=evaluator._parse_js) as parser:
            report = evaluate_tests({"javascript": source}, tests, language="web")

        parser.assert_called_once()
        self.assertEqual(report.status, "passed")

    def test_schema_rejects_dynamic_or_unsupported_javaScript_queries(self):
        invalid_definitions = [
            ("js.call_used", {"name": "console.log", "args": [{"dynamic": "no"}]}),
            ("js.call_used", {"name": "console.log; eval"}),
            ("js.variable_declared", {"name": "dato", "expected": [["lista"]]}),
            ("js.variable_declared", {"name": "dato", "expected": float("nan")}),
            ("js.node_kind", {"kind": "program"}),
            ("js.node_kind", {"kind": "array", "arbitrary": True}),
        ]
        for test_type, definition in invalid_definitions:
            with self.subTest(test_type=test_type, definition=definition):
                with self.assertRaises(ValueError):
                    validate_test_definition(test_type, definition)
