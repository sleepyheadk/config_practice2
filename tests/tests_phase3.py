"""Тесты этапа 3: граф зависимостей, фильтр, циклы, тестовый режим."""
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "src"))

sys.path.insert(0, SRC_DIR)

import dependencies  # noqa: E402
import file_repository  # noqa: E402
import graph  # noqa: E402
import main  # noqa: E402
import report  # noqa: E402
import validation  # noqa: E402
from errors import ConfigError, RepositoryError  # noqa: E402

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


def write_temp(test_case, text):
    """Создаёт временный файл с текстом и возвращает путь к нему."""
    tmp = tempfile.TemporaryDirectory()
    test_case.addCleanup(tmp.cleanup)
    path = os.path.join(tmp.name, "graph.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)
    return path


def provider(data):
    """Делает функцию «пакет -> зависимости» из словаря."""
    return lambda package: list(data[package])


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


class TestFileRepository(unittest.TestCase):
    """Чтение и разбор файла тестового репозитория."""

    def test_parse(self):
        """Комментарии и пустые строки игнорируются, повторы убираются."""
        text = "A: B C B\n\n# комментарий\nB:\nC: B  # хвост\n"
        self.assertEqual(
            file_repository.parse_repository(text),
            {"A": ["B", "C"], "B": [], "C": ["B"]})

    def test_invalid_text(self):
        """Ошибки формата вызывают RepositoryError."""
        texts = ["A B", ": B", "a: B", "A: b", "A: B1", "A:\nA:", "",
                 "# только комментарий"]
        for text in texts:
            with self.subTest(text=text):
                with self.assertRaises(RepositoryError):
                    file_repository.parse_repository(text)

    def test_error_has_line_number(self):
        """В сообщении об ошибке указан номер строки."""
        with self.assertRaisesRegex(RepositoryError, "строка 2"):
            file_repository.parse_repository("A: B\nbad line")

    def test_lookup(self):
        """Известные пакеты находятся, неизвестные дают ошибку."""
        lookup = file_repository.make_lookup({"A": ["B"]})
        self.assertEqual(lookup("A"), ["B"])
        self.assertEqual(lookup("B"), [])
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            lookup("Z")

    def test_missing_file(self):
        """Несуществующий файл даёт RepositoryError."""
        with self.assertRaises(RepositoryError):
            file_repository.make_file_provider("no_such_file.txt")

    def test_provider_from_file(self):
        """Функция, созданная по файлу, возвращает зависимости."""
        lookup = file_repository.make_file_provider(
            write_temp(self, GRAPH_TEXT))
        self.assertEqual(lookup("A"), ["B", "C"])


class TestBuildGraph(unittest.TestCase):
    """Обход графа в глубину."""

    def test_diamond(self):
        """Общая зависимость обрабатывается один раз, порядок DFS."""
        data = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        result = graph.build_graph("A", provider(data))
        self.assertEqual(result.graph, data)
        self.assertEqual(list(result.graph), ["A", "B", "D", "C"])
        self.assertEqual(result.cycles, [])

    def test_each_package_requested_once(self):
        """Зависимости каждого пакета запрашиваются один раз."""
        data = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        calls = []

        def get(package):
            calls.append(package)
            return data[package]

        graph.build_graph("A", get)
        self.assertEqual(sorted(calls), ["A", "B", "C", "D"])

    def test_cycle(self):
        """Цикл найден, обход завершается."""
        data = {"E": ["F"], "F": ["G"], "G": ["E"]}
        result = graph.build_graph("E", provider(data))
        self.assertEqual(result.graph, data)
        self.assertEqual(result.cycles, [["E", "F", "G", "E"]])

    def test_self_dependency(self):
        """Пакет, зависящий от себя, считается циклом."""
        result = graph.build_graph("H", provider({"H": ["H"]}))
        self.assertEqual(result.graph, {"H": ["H"]})
        self.assertEqual(result.cycles, [["H", "H"]])

    def test_filter(self):
        """Пакеты с подстрокой в имени исключаются (без учёта регистра)."""
        data = {"K": ["KA", "KB", "LA"], "KB": []}
        result = graph.build_graph("K", provider(data), "a")
        self.assertEqual(result.graph, {"K": ["KB"], "KB": []})

    def test_long_chain_without_recursion(self):
        """Цепочка длиннее лимита рекурсии обходится без ошибки."""
        size = 2000
        data = {str(i): [str(i + 1)] for i in range(size - 1)}
        data[str(size - 1)] = []
        result = graph.build_graph("0", provider(data))
        self.assertEqual(len(result.graph), size)

    def test_source_error_propagates(self):
        """Ошибка источника данных не перехватывается."""
        def get(package):
            raise RepositoryError("сбой")

        with self.assertRaises(RepositoryError):
            graph.build_graph("A", get)


class TestMakeSource(unittest.TestCase):
    """Выбор источника данных."""

    def test_test_mode(self):
        """В тестовом режиме данные берутся из файла, имя не меняется."""
        path = write_temp(self, GRAPH_TEXT)
        root, get = dependencies.make_source("A", path, True)
        self.assertEqual(root, "A")
        self.assertEqual(get("A"), ["B", "C"])

    def test_online_mode(self):
        """В обычном режиме имя нормализуется, запрос идёт в репозиторий."""
        with patch("dependencies.get_direct_dependencies",
                   return_value=["idna"]) as fetch:
            root, get = dependencies.make_source(
                "Charset_Normalizer", "https://x.org", False)
            self.assertEqual(get("urllib3"), ["idna"])
        self.assertEqual(root, "charset-normalizer")
        fetch.assert_called_once_with("urllib3", repo="https://x.org")


class TestReport(unittest.TestCase):
    """Текстовый отчёт."""

    def test_without_cycles(self):
        """Граф без циклов."""
        result = graph.GraphResult({"A": ["B"], "B": []}, [])
        self.assertEqual(
            report.format_report("A", result),
            "Граф зависимостей пакета A:\n"
            "A -> B\n"
            "B -> (нет зависимостей)\n"
            "Циклических зависимостей нет")

    def test_with_cycles(self):
        """Циклы выводятся цепочками."""
        result = graph.GraphResult(
            {"E": ["F"], "F": ["E"]}, [["E", "F", "E"]])
        text = report.format_report("E", result)
        self.assertIn("Циклические зависимости:\nE -> F -> E", text)


class TestValidateFilter(unittest.TestCase):
    """Проверка фильтра."""

    def test_valid(self):
        """Пустой фильтр и фильтр, не задевающий пакет, проходят."""
        validation.validate_filter("", "A")
        validation.validate_filter("x", "A")

    def test_excludes_package(self):
        """Фильтр, входящий в имя пакета, вызывает ошибку."""
        for substring, package in [("a", "Abc"), ("ABC", "abc")]:
            with self.subTest(substring=substring):
                with self.assertRaises(ConfigError):
                    validation.validate_filter(substring, package)


class TestMain(unittest.TestCase):
    """Работа программы целиком в тестовом режиме."""

    def setUp(self):
        """Создаёт файл тестового репозитория."""
        self.path = write_temp(self, GRAPH_TEXT)

    def run_test_mode(self, package, *extra):
        """Запускает программу на тестовом файле."""
        return run_main("--package", package, "--repo", self.path,
                        "--test-mode", *extra)

    def test_diamond(self):
        """Граф без циклов."""
        code, out, _ = self.run_test_mode("A")
        self.assertEqual(code, 0)
        self.assertIn("A -> B, C", out)
        self.assertIn("Циклических зависимостей нет", out)

    def test_cycle(self):
        """Цикл выводится в отчёте."""
        code, out, _ = self.run_test_mode("E")
        self.assertEqual(code, 0)
        self.assertIn("E -> F -> G -> E", out)

    def test_filter(self):
        """Отфильтрованные пакеты не выводятся."""
        code, out, _ = self.run_test_mode("K", "--filter", "KA")
        self.assertEqual(code, 0)
        self.assertIn("K -> KB", out)
        self.assertNotIn("KA", out)

    def test_filter_excludes_root(self):
        """Фильтр, исключающий корневой пакет, даёт ошибку."""
        code, _, err = self.run_test_mode("A", "--filter", "a")
        self.assertEqual(code, 1)
        self.assertIn("фильтр", err)

    def test_unknown_package(self):
        """Пакета нет в тестовом репозитории."""
        code, _, err = self.run_test_mode("Z")
        self.assertEqual(code, 1)
        self.assertIn("не найден", err)

    def test_bad_file_format(self):
        """Файл с ошибкой формата даёт сообщение с номером строки."""
        bad = write_temp(self, "bad line\n")
        code, _, err = run_main("--package", "A", "--repo", bad,
                                "--test-mode")
        self.assertEqual(code, 1)
        self.assertIn("строка 1", err)

    def test_online_error(self):
        """Ошибка репозитория в обычном режиме даёт код 1."""
        error = RepositoryError("нет связи")
        with patch("dependencies.get_direct_dependencies",
                   side_effect=error):
            code, _, err = run_main("--package", "requests",
                                    "--repo", "https://x.org")
        self.assertEqual(code, 1)
        self.assertIn("Ошибка: нет связи", err)


if __name__ == "__main__":
    unittest.main()
