"""Тесты этапа 4: порядок загрузки зависимостей."""
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "src"))

sys.path.insert(0, SRC_DIR)

import cli  # noqa: E402
import graph  # noqa: E402
import load_order  # noqa: E402
import main  # noqa: E402
import report  # noqa: E402

GRAPH_TEXT = """\
A: B C
B: D
C: D
D:
E: F
F: G
G: E
K: KA KB
"""


def order_of(root, data, substring=""):
    """Строит граф по словарю и возвращает порядок загрузки."""
    result = graph.build_graph(
        root, lambda package: list(data[package]), substring)
    return load_order.build_load_order(root, result.graph)


def write_temp(test_case, text):
    """Создаёт временный файл с текстом и возвращает путь к нему."""
    tmp = tempfile.TemporaryDirectory()
    test_case.addCleanup(tmp.cleanup)
    path = os.path.join(tmp.name, "graph.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)
    return path


def run_main(*argv):
    """Запускает main.main() и возвращает код выхода, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with patch.object(sys, "argv", ["main.py", *argv]):
        with patch("sys.stdout", out), patch("sys.stderr", err):
            try:
                main.main()
            except SystemExit as exit_info:
                code = exit_info.code
    return code, out.getvalue(), err.getvalue()


class TestLoadOrder(unittest.TestCase):
    """Построение порядка загрузки."""

    def assert_dependencies_first(self, data, order):
        """Каждая зависимость стоит в списке раньше зависящего пакета."""
        for package in order:
            for dependency in data[package]:
                with self.subTest(package=package, dependency=dependency):
                    self.assertLess(
                        order.index(dependency), order.index(package))

    def test_diamond(self):
        """Общая зависимость ставится один раз и раньше остальных."""
        data = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(order_of("A", data), ["D", "B", "C", "A"])

    def test_chain(self):
        """В цепочке порядок обратный записи зависимостей."""
        data = {"M": ["N"], "N": ["O"], "O": ["P"], "P": []}
        self.assertEqual(order_of("M", data), ["P", "O", "N", "M"])

    def test_several_levels(self):
        """Несколько уровней с общими зависимостями."""
        data = {"R": ["S", "T"], "S": ["U", "V"], "T": ["V", "W"],
                "U": ["W"], "V": [], "W": []}
        order = order_of("R", data)
        self.assertEqual(order, ["W", "U", "V", "S", "T", "R"])
        self.assert_dependencies_first(data, order)

    def test_root_is_last(self):
        """Корневой пакет всегда последний, повторов нет."""
        data = {"A": ["B", "C"], "B": ["C"], "C": []}
        order = order_of("A", data)
        self.assertEqual(order[-1], "A")
        self.assertEqual(len(order), len(set(order)))

    def test_no_dependencies(self):
        """Пакет без зависимостей даёт порядок из одного пакета."""
        self.assertEqual(order_of("A", {"A": []}), ["A"])

    def test_cycle(self):
        """Цикл не вызывает зависания, все пакеты попадают в порядок."""
        data = {"E": ["F"], "F": ["G"], "G": ["E"]}
        self.assertEqual(order_of("E", data), ["G", "F", "E"])

    def test_cycle_inside_graph(self):
        """Цикл посреди графа: корень вне цикла стоит последним."""
        data = {"X": ["Y"], "Y": ["Z"], "Z": ["Y", "ZZ"], "ZZ": []}
        self.assertEqual(order_of("X", data), ["ZZ", "Z", "Y", "X"])

    def test_self_dependency(self):
        """Пакет, зависящий от себя, встречается один раз."""
        self.assertEqual(order_of("H", {"H": ["H"]}), ["H"])

    def test_filter(self):
        """Отфильтрованные пакеты не попадают в порядок."""
        data = {"R": ["S", "T"], "S": ["U", "V"], "T": ["V", "W"],
                "U": ["W"], "V": [], "W": []}
        order = order_of("R", data, "V")
        self.assertEqual(order, ["W", "U", "S", "T", "R"])

    def test_long_chain_without_recursion(self):
        """Цепочка длиннее лимита рекурсии обрабатывается без ошибки."""
        size = 2000
        data = {str(i): [str(i + 1)] for i in range(size - 1)}
        data[str(size - 1)] = []
        order = order_of("0", data)
        self.assertEqual(len(order), size)
        self.assertEqual(order[0], str(size - 1))
        self.assertEqual(order[-1], "0")


class TestReport(unittest.TestCase):
    """Текст с порядком загрузки."""

    def test_format_order(self):
        """Пакеты нумеруются с единицы."""
        self.assertEqual(report.format_order(["D", "A"]), ["1. D", "2. A"])

    def test_without_cycles(self):
        """Без циклов предупреждения нет."""
        text = report.format_load_order("A", ["D", "A"], [])
        self.assertEqual(
            text, "Порядок загрузки зависимостей пакета A:\n1. D\n2. A")

    def test_with_cycles(self):
        """С циклами добавляется предупреждение и сами циклы."""
        text = report.format_load_order("E", ["F", "E"], [["E", "F", "E"]])
        self.assertIn(report.CYCLE_WARNING, text)
        self.assertTrue(text.endswith("E -> F -> E"))


class TestCli(unittest.TestCase):
    """Параметр --load-order."""

    def parse(self, *argv):
        """Разбирает аргументы, подменяя sys.argv."""
        with patch.object(sys, "argv", ["main.py", *argv]):
            return cli.parse_args()

    def test_default(self):
        """По умолчанию режим выключен."""
        self.assertFalse(self.parse("--package", "a").load_order)

    def test_enabled(self):
        """Флаг включает режим."""
