"""Тесты этапа 1: параметры командной строки и их проверка."""
import argparse
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import src.main as main
from src.main import ConfigError


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PATH = os.path.abspath(os.path.join(TESTS_DIR, "..", "src", "main.py"))
sys.path.insert(0, os.path.dirname(MAIN_PATH))


def make_args(**overrides):
    """Создаёт набор корректных параметров, подменяя нужные."""
    values = {
        "package": "requests",
        "repo": "https://pypi.org/pypi",
        "test_mode": False,
        "output": "graph.svg",
        "ascii_tree": False,
        "filter": "",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class TestValidatePackage(unittest.TestCase):
    """Проверка имени пакета."""

    def test_valid_names(self):
        """Корректные имена не вызывают ошибок."""
        names = ["requests", "Flask", "zope.interface", "my-pkg_2", "A", "a1"]
        for name in names:
            with self.subTest(name=name):
                main.validate_package(name)

    def test_invalid_names(self):
        """Некорректные имена вызывают ConfigError."""
        names = ["", "   ", "-bad", "bad-", ".bad", "bad name", "pkg$", "а"]
        for name in names:
            with self.subTest(name=name):
                with self.assertRaises(ConfigError):
                    main.validate_package(name)

    def test_none(self):
        """Незаданное имя даёт ошибку с упоминанием --package."""
        with self.assertRaisesRegex(ConfigError, "--package"):
            main.validate_package(None)


class TestValidateRepo(unittest.TestCase):
    """Проверка URL репозитория и пути к тестовому файлу."""

    def setUp(self):
        """Создаёт временную папку с тестовым файлом."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file_path = os.path.join(self.tmp.name, "graph.txt")
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write("A: B\n")

    def test_valid_urls(self):
        """Корректные URL проходят в обычном режиме."""
        urls = ["https://pypi.org/pypi", "http://localhost:8000/simple"]
        for url in urls:
            with self.subTest(url=url):
                main.validate_repo(url, False)

    def test_invalid_urls(self):
        """Некорректные URL вызывают ошибку."""
        urls = ["pypi.org", "ftp://pypi.org", "http://", "just text"]
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ConfigError):
                    main.validate_repo(url, False)

    def test_none(self):
        """Незаданный репозиторий даёт ошибку с упоминанием --repo."""
        with self.assertRaisesRegex(ConfigError, "--repo"):
            main.validate_repo(None, False)

    def test_empty(self):
        """Пустая строка и пробелы не допускаются."""
        for value in ["", "   "]:
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    main.validate_repo(value, False)

    def test_test_mode_existing_file(self):
        """В тестовом режиме существующий файл проходит."""
        main.validate_repo(self.file_path, True)

    def test_test_mode_missing_file(self):
        """В тестовом режиме несуществующий файл даёт ошибку."""
        missing = os.path.join(self.tmp.name, "nope.txt")
        with self.assertRaises(ConfigError):
            main.validate_repo(missing, True)

    def test_test_mode_directory(self):
        """В тестовом режиме папка вместо файла даёт ошибку."""
        with self.assertRaises(ConfigError):
            main.validate_repo(self.tmp.name, True)

    def test_test_mode_rejects_url(self):
        """В тестовом режиме URL не считается файлом."""
        with self.assertRaises(ConfigError):
            main.validate_repo("https://pypi.org/pypi", True)

    def test_normal_mode_rejects_file_path(self):
        """В обычном режиме путь к файлу не считается URL."""
        with self.assertRaises(ConfigError):
            main.validate_repo(self.file_path, False)


class TestValidateOutput(unittest.TestCase):
    """Проверка имени выходного файла."""

    def setUp(self):
        """Создаёт временную папку."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_valid_names(self):
        """Корректные имена проходят."""
        names = ["graph.svg", "GRAPH.SVG", os.path.join(self.tmp.name, "a.svg")]
        for name in names:
            with self.subTest(name=name):
                main.validate_output(name)

    def test_invalid_names(self):
        """Пустое имя и неверное расширение вызывают ошибку."""
        names = ["", "   ", "graph.png", "graph", "graph.svg.txt"]
        for name in names:
            with self.subTest(name=name):
                with self.assertRaises(ConfigError):
                    main.validate_output(name)

    def test_missing_folder(self):
        """Несуществующая папка вызывает ошибку."""
        path = os.path.join(self.tmp.name, "nope", "graph.svg")
        with self.assertRaises(ConfigError):
            main.validate_output(path)

    def test_output_is_directory(self):
        """Имя, совпадающее с папкой, вызывает ошибку."""
        path = os.path.join(self.tmp.name, "dir.svg")
        os.mkdir(path)
        with self.assertRaises(ConfigError):
            main.validate_output(path)


class TestValidateArgs(unittest.TestCase):
    """Проверка всех параметров вместе."""

    def test_valid(self):
        """Корректный набор параметров проходит."""
        main.validate_args(make_args())

    def test_bad_package(self):
        """Ошибка в имени пакета обнаруживается."""
        with self.assertRaisesRegex(ConfigError, "--package"):
            main.validate_args(make_args(package=None))

    def test_bad_repo(self):
        """Ошибка в репозитории обнаруживается."""
        with self.assertRaisesRegex(ConfigError, "--repo"):
            main.validate_args(make_args(repo=None))

    def test_bad_output(self):
        """Ошибка в имени выходного файла обнаруживается."""
        with self.assertRaises(ConfigError):
            main.validate_args(make_args(output="graph.png"))


class TestParseArgs(unittest.TestCase):
    """Разбор аргументов командной строки."""

    def parse(self, *argv):
        """Разбирает аргументы, подменяя sys.argv."""
        with patch.object(sys, "argv", ["main.py", *argv]):
            return main.parse_args()

    def test_defaults(self):
        """Значения по умолчанию."""
        args = self.parse("--package", "a", "--repo", "r")
        self.assertEqual(args.output, "graph.svg")
        self.assertFalse(args.test_mode)
        self.assertFalse(args.ascii_tree)
        self.assertEqual(args.filter, "")

    def test_all_values(self):
        """Все параметры считываются."""
        args = self.parse(
            "--package", "pkg", "--repo", "repo", "--test-mode",
            "--output", "out.svg", "--ascii-tree", "--filter", "test",
        )
        self.assertEqual(args.package, "pkg")
        self.assertEqual(args.repo, "repo")
        self.assertTrue(args.test_mode)
        self.assertEqual(args.output, "out.svg")
        self.assertTrue(args.ascii_tree)
        self.assertEqual(args.filter, "test")

    def test_unknown_option(self):
        """Неизвестная опция завершает программу."""
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                self.parse("--unknown", "x")


class TestCommandLine(unittest.TestCase):
    """Запуск программы как отдельного процесса."""

    def setUp(self):
        """Создаёт временный тестовый файл репозитория."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file_path = os.path.join(self.tmp.name, "graph.txt")
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write("A: B\n")

    def run_main(self, *args):
        """Запускает main.py с аргументами и возвращает результат."""
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run(
            [sys.executable, MAIN_PATH, *args],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )

    def assert_fails(self, result, text):
        """Проверяет код 1, сообщение об ошибке и отсутствие трейсбэка."""
        self.assertEqual(result.returncode, 1)
        self.assertIn("Ошибка:", result.stderr)
        self.assertIn(text, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_success(self):
        """Корректный запуск выводит все параметры."""
        result = self.run_main("--package", "requests",
                               "--repo", "https://pypi.org/pypi")
        self.assertEqual(result.returncode, 0)
        for line in ["package: requests", "repo: https://pypi.org/pypi",
                     "test_mode: False", "output: graph.svg",
                     "ascii_tree: False", "filter: "]:
            self.assertIn(line, result.stdout)

    def test_success_all_options(self):
        """Запуск со всеми опциями в тестовом режиме."""
        result = self.run_main(
            "--package", "A", "--repo", self.file_path, "--test-mode",
            "--output", "x.svg", "--ascii-tree", "--filter", "test",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("test_mode: True", result.stdout)
        self.assertIn("ascii_tree: True", result.stdout)
        self.assertIn("filter: test", result.stdout)

    def test_no_arguments(self):
        """Запуск без параметров."""
        self.assert_fails(self.run_main(), "--package")

    def test_missing_repo(self):
        """Не задан репозиторий."""
        self.assert_fails(self.run_main("--package", "a"), "--repo")

    def test_empty_package(self):
        """Пустое имя пакета."""
        result = self.run_main("--package", "", "--repo", "https://a.org")
        self.assert_fails(result, "пакета")

    def test_bad_url(self):
        """Некорректный URL."""
        result = self.run_main("--package", "a", "--repo", "pypi.org")
        self.assert_fails(result, "URL")

    def test_test_mode_missing_file(self):
        """Тестовый режим с несуществующим файлом."""
        result = self.run_main("--package", "A", "--repo", "nofile.txt",
                               "--test-mode")
        self.assert_fails(result, "файл")

    def test_bad_extension(self):
        """Неверное расширение выходного файла."""
        result = self.run_main("--package", "a", "--repo", "https://a.org",
                               "--output", "graph.png")
        self.assert_fails(result, ".svg")


if __name__ == "__main__":
    unittest.main()
