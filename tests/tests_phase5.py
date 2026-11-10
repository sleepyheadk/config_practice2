"""Тесты этапа 5: ASCII-дерево, текст DOT, сохранение SVG."""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "src"))

sys.path.insert(0, SRC_DIR)

import ascii_tree
import dot_format
import main
import render
from errors import RenderError

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

DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
CYCLE = {"E": ["F"], "F": ["G"], "G": ["E"]}


def make_tmp(test_case):
    """Создаёт временную папку и возвращает путь к ней."""
    tmp = tempfile.TemporaryDirectory()
    test_case.addCleanup(tmp.cleanup)
    return tmp.name


def write_temp(test_case, text):
    """Создаёт временный файл с текстом и возвращает путь к нему."""
    path = os.path.join(make_tmp(test_case), "graph.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)
    return path


def read_file(path):
    """Читает текстовый файл целиком."""
    with open(path, encoding="utf-8") as file:
        return file.read()


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


class TestAsciiTree(unittest.TestCase):
    """Текстовое дерево зависимостей."""

    def test_diamond(self):
        """Простое дерево с общей зависимостью без собственных."""
        expected = "\n".join([
            "A",
            "|-- B",
            "|   `-- D",
            "`-- C",
            "    `-- D",
        ])
        self.assertEqual(ascii_tree.build_tree("A", DIAMOND), expected)

    def test_repeated_subtree_is_not_expanded(self):
        """Повтор пакета с зависимостями помечается и не раскрывается."""
        data = dict(DIAMOND, D=["E"], E=[])
        expected = "\n".join([
            "A",
            "|-- B",
            "|   `-- D",
            "|       `-- E",
            "`-- C",
            "    `-- D (см. выше)",
        ])
        self.assertEqual(ascii_tree.build_tree("A", data), expected)

    def test_several_levels(self):
        """Вертикальная линия тянется, пока есть соседние ветки."""
        data = {"R": ["S", "T"], "S": ["U", "V"], "T": ["V", "W"],
                "U": ["W"], "V": [], "W": []}
        expected = "\n".join([
            "R",
            "|-- S",
            "|   |-- U",
            "|   |   `-- W",
            "|   `-- V",
            "`-- T",
            "    |-- V",
            "    `-- W",
        ])
        self.assertEqual(ascii_tree.build_tree("R", data), expected)

    def test_cycle(self):
        """Пакет, замыкающий цикл, помечается и не раскрывается."""
        expected = "\n".join([
            "E",
            "`-- F",
            "    `-- G",
            "        `-- E (цикл)",
        ])
        self.assertEqual(ascii_tree.build_tree("E", CYCLE), expected)

    def test_self_dependency(self):
        """Зависимость пакета от самого себя - цикл."""
        self.assertEqual(
            ascii_tree.build_tree("H", {"H": ["H"]}), "H\n`-- H (цикл)")

    def test_no_dependencies(self):
        """Пакет без зависимостей даёт одну строку."""
        self.assertEqual(ascii_tree.build_tree("A", {"A": []}), "A")

    def test_long_chain_without_recursion(self):
        """Цепочка длиннее лимита рекурсии строится без ошибки."""
        size = 1200
        data = {str(i): [str(i + 1)] for i in range(size - 1)}
        data[str(size - 1)] = []
        lines = ascii_tree.build_tree("0", data).split("\n")
        self.assertEqual(len(lines), size)


class TestDotFormat(unittest.TestCase):
    """Текст графа на языке Graphviz."""

    def test_quote(self):
        """Имена берутся в кавычки, служебные символы экранируются."""
        self.assertEqual(dot_format.quote("a-b"), '"a-b"')
        self.assertEqual(dot_format.quote('a"b'), '"a\\"b"')
        self.assertEqual(dot_format.quote("a\\b"), '"a\\\\b"')

    def test_diamond(self):
        """Заголовок, корень и все рёбра на месте."""
        text = dot_format.build_dot("A", DIAMOND)
        self.assertTrue(text.startswith('digraph "A" {\n'))
        self.assertTrue(text.endswith("}\n"))
        self.assertIn('"A" [style=filled', text)
        for edge in ['"A" -> "B";', '"A" -> "C";',
                     '"B" -> "D";', '"C" -> "D";']:
            with self.subTest(edge=edge):
                self.assertIn(edge, text)
        self.assertEqual(text.count("->"), 4)

    def test_root_without_dependencies(self):
        """Пакет без зависимостей попадает в картинку как отдельный узел."""
        text = dot_format.build_dot("A", {"A": []})
        self.assertIn('"A" [style=filled', text)
        self.assertNotIn("->", text)

    def test_closing_edges(self):
        """Ребро, замыкающее цикл, - последняя пара цикла."""
        cycles = [["E", "F", "G", "E"], ["H", "H"]]
        self.assertEqual(
            dot_format.closing_edges(cycles), {("G", "E"), ("H", "H")})

    def test_cycle_edge_is_red(self):
        """Только замыкающее ребро цикла выделено красным."""
        text = dot_format.build_dot("E", CYCLE, [["E", "F", "G", "E"]])
        self.assertIn('"G" -> "E" [color=red', text)
        self.assertIn('    "E" -> "F";\n', text)


class TestRender(unittest.TestCase):
    """Сохранение файлов и запуск Graphviz (сам dot подменяется)."""

    @staticmethod
    def fake_result(returncode=0, stdout="<svg/>", stderr=""):
        """Создаёт подменный результат запуска программы."""
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_dot_file_path(self):
        """DOT-файл лежит рядом с SVG и отличается расширением."""
        nested = os.path.join("docs", "a.svg")
        expected = os.path.join("docs", "a.dot")
        self.assertEqual(render.dot_file_path("graph.svg"), "graph.dot")
        self.assertEqual(render.dot_file_path(nested), expected)

    def test_run_dot_ok(self):
        """DOT-текст передаётся в dot, возвращается SVG."""
        with patch("render.subprocess.run",
                   return_value=self.fake_result()) as run:
            svg = render.run_dot("digraph {}")
        self.assertEqual(svg, "<svg/>")
        self.assertEqual(run.call_args[0][0], ["dot", "-Tsvg"])
        self.assertEqual(run.call_args[1]["input"], "digraph {}")

    def test_run_dot_failures(self):
        """Все сбои запуска превращаются в RenderError."""
        cases = [
            ("не найден", FileNotFoundError()),
            ("не ответил", subprocess.TimeoutExpired("dot", 60)),
            ("не удалось запустить", PermissionError("нет прав")),
        ]
        for text, error in cases:
            with self.subTest(text=text):
                with patch("render.subprocess.run", side_effect=error):
                    with self.assertRaisesRegex(RenderError, text):
                        render.run_dot("digraph {}")

    def test_run_dot_error_code(self):
        """Ненулевой код возврата включает сообщение Graphviz."""
        result = self.fake_result(returncode=1, stderr="syntax error\n")
        with patch("render.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RenderError, "syntax error"):
                render.run_dot("bad")

    def test_save_graph(self):
        """Сохраняются и DOT-файл, и SVG."""
        output = os.path.join(make_tmp(self), "g.svg")
        with patch("render.run_dot", return_value="<svg/>"):
            dot_path = render.save_graph("digraph {}\n", output)
        self.assertEqual(dot_path, output[:-4] + ".dot")
        self.assertEqual(read_file(dot_path), "digraph {}\n")
        self.assertEqual(read_file(output), "<svg/>")

    def test_dot_file_kept_without_graphviz(self):
        """Если Graphviz недоступен, DOT-файл всё равно сохраняется."""
        output = os.path.join(make_tmp(self), "g.svg")
        with patch("render.run_dot", side_effect=RenderError("нет")):
            with self.assertRaises(RenderError):
                render.save_graph("digraph {}\n", output)
        self.assertTrue(os.path.exists(output[:-4] + ".dot"))
        self.assertFalse(os.path.exists(output))

    def test_unwritable_path(self):
        """Невозможность записи файла даёт RenderError."""
        output = os.path.join(make_tmp(self), "nope", "g.svg")
        with self.assertRaisesRegex(RenderError, "не удалось записать"):
            render.save_graph("digraph {}\n", output)


class TestMain(unittest.TestCase):
    """Работа программы целиком (сохранение файлов подменяется)."""

    def set_up(self):
        """Создаёт файл тестового репозитория."""
        self.path = write_temp(self, GRAPH_TEXT)

    def run_visual(self, package, *extra, **save_kwargs):
        """Запускает программу на тестовом файле, возвращает итог и mock."""
        save_kwargs.setdefault("return_value", "graph.dot")
        with patch("main.save_graph", **save_kwargs) as saver:
            result = run_main("--package", package, "--repo", self.path,
                              "--test-mode", *extra)
        return result, saver

    def test_saves_graph(self):
        """По умолчанию граф сохраняется в graph.svg."""
        (code, out, _), saver = self.run_visual("A")
        self.assertEqual(code, 0)
        saver.assert_called_once()
        dot_text, output = saver.call_args[0]
        self.assertEqual(output, "graph.svg")
        self.assertIn('"A" -> "B";', dot_text)
        self.assertIn("Граф сохранён: graph.svg", out)
        self.assertIn("graph.dot", out)
        self.assertNotIn("|--", out)

    def test_custom_output(self):
        """Имя файла берётся из --output."""
        _, saver = self.run_visual("A", "--output", "out.svg")
        self.assertEqual(saver.call_args[0][1], "out.svg")

    def test_ascii_tree(self):
        """С --ascii-tree дерево выводится перед сообщением о файле."""
        (code, out, _), _ = self.run_visual("A", "--ascii-tree")
        self.assertEqual(code, 0)
        self.assertIn("|-- B", out)
        self.assertIn("`-- C", out)
        self.assertLess(out.index("|-- B"), out.index("Граф сохранён"))

    def test_cycle_edge_in_dot(self):
        """Ребро, замыкающее цикл, попадает в DOT выделенным."""
        _, saver = self.run_visual("E")
        self.assertIn("color=red", saver.call_args[0][0])

    def test_filter(self):
        """Отфильтрованные пакеты не попадают в DOT."""
        _, saver = self.run_visual("K", "--filter", "KA")
        dot_text = saver.call_args[0][0]
        self.assertIn('"K" -> "KB";', dot_text)
        self.assertNotIn("KA", dot_text)

    def test_load_order_does_not_render(self):
        """Режим --load-order файлы не создаёт."""
        (code, out, _), saver = self.run_visual("A", "--load-order")
        self.assertEqual(code, 0)
        saver.assert_not_called()
        self.assertIn("Порядок загрузки", out)

    def test_render_error(self):
        """Ошибка рисования даёт сообщение и код 1."""
        (code, _, err), _ = self.run_visual(
            "A", side_effect=RenderError("нет Graphviz"))
        self.assertEqual(code, 1)
        self.assertIn("Ошибка: нет Graphviz", err)

    def test_tree_printed_before_render_error(self):
        """Дерево выводится, даже если Graphviz недоступен."""
        (code, out, _), _ = self.run_visual(
            "A", "--ascii-tree", side_effect=RenderError("нет Graphviz"))
        self.assertEqual(code, 1)
        self.assertIn("`-- C", out)

    def test_unknown_package(self):
        """Ошибка данных возникает до рисования."""
        (code, _, err), saver = self.run_visual("Z")
        self.assertEqual(code, 1)
        self.assertIn("не найден", err)
        saver.assert_not_called()

    def test_online_mode(self):
        """Обычный режим: данные из репозитория (запрос подменён)."""
        data = {"requests": ["idna"], "idna": []}
        with patch("dependencies.get_direct_dependencies",
                   side_effect=lambda package, repo: data[package]):
            with patch("main.save_graph", return_value="g.dot") as saver:
                code, _, _ = run_main("--package", "Requests",
                                      "--repo", "https://x.org")
        self.assertEqual(code, 0)
        self.assertIn('"requests" -> "idna";', saver.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
