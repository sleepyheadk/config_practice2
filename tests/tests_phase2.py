"""Тесты этапа 2: получение и разбор прямых зависимостей пакета."""
import io
import os
import sys
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "src"))

sys.path.insert(0, SRC_DIR)

import dependencies  # noqa: E402
import main  # noqa: E402
import repository  # noqa: E402
import requirement  # noqa: E402
from errors import RepositoryError  # noqa: E402


def fake_response(body):
    """Создаёт подменный ответ сервера с заданным телом."""
    response = MagicMock()
    response.__enter__.return_value.read.return_value = body
    return response


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


class TestRequirement(unittest.TestCase):
    """Разбор строк зависимостей."""

    def test_name_and_specifier(self):
        """Имя и версии разделяются."""
        req = requirement.parse_requirement("urllib3<3,>=1.21.1")
        self.assertEqual(req.name, "urllib3")
        self.assertEqual(req.specifier, "<3,>=1.21.1")
        self.assertEqual(req.marker, "")

    def test_name_is_normalized(self):
        """Имя приводится к нижнему регистру с дефисами."""
        req = requirement.parse_requirement("charset_normalizer<4,>=2")
        self.assertEqual(req.name, "charset-normalizer")

    def test_without_version(self):
        """Зависимость без версии."""
        req = requirement.parse_requirement("certifi")
        self.assertEqual(req.name, "certifi")
        self.assertEqual(req.specifier, "")

    def test_old_style_with_extras(self):
        """Скобки и extras в имени отбрасываются."""
        req = requirement.parse_requirement("requests[security] (>=2.0)")
        self.assertEqual(req.name, "requests")
        self.assertEqual(req.specifier, ">=2.0")

    def test_is_extra(self):
        """Зависимость с условием extra опциональна."""
        line = 'PySocks!=1.5.7,>=1.5.6; extra == "socks"'
        req = requirement.parse_requirement(line)
        self.assertEqual(req.name, "pysocks")
        self.assertTrue(requirement.is_extra(req))

    def test_other_marker_is_not_extra(self):
        """Другие условия не делают зависимость опциональной."""
        line = 'colorama; sys_platform == "win32"'
        req = requirement.parse_requirement(line)
        self.assertFalse(requirement.is_extra(req))

    def test_invalid_line(self):
        """Строка без имени вызывает RepositoryError."""
        for line in ["", "<3"]:
            with self.subTest(line=line):
                with self.assertRaises(RepositoryError):
                    requirement.parse_requirement(line)


class TestRepository(unittest.TestCase):
    """Получение метаданных пакета (сеть подменяется)."""

    def test_build_url(self):
        """Адрес собирается с учётом слеша в конце."""
        expected = "https://pypi.org/pypi/requests/json"
        for repo in ["https://pypi.org/pypi", "https://pypi.org/pypi/"]:
            with self.subTest(repo=repo):
                self.assertEqual(
                    repository.build_url(repo, "requests"), expected)

    def test_fetch_ok(self):
        """Корректный JSON возвращается словарём."""
        response = fake_response(b'{"info": {"name": "a"}}')
        with patch("urllib.request.urlopen", return_value=response):
            data = repository.fetch_package_info("https://x.org", "a")
        self.assertEqual(data, {"info": {"name": "a"}})

    def test_package_not_found(self):
        """Ответ 404 даёт понятную ошибку."""
        error = urllib.error.HTTPError("https://x.org", 404, "", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RepositoryError, "не найден"):
                repository.fetch_package_info("https://x.org", "a")

    def test_no_connection(self):
        """Недоступный сервер даёт понятную ошибку."""
        error = urllib.error.URLError("no network")
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RepositoryError, "подключиться"):
                repository.fetch_package_info("https://x.org", "a")

    def test_bad_json(self):
        """Ответ не в формате JSON даёт ошибку."""
        for body in [b"<html></html>", b"[1, 2]"]:
            with self.subTest(body=body):
                response = fake_response(body)
                with patch("urllib.request.urlopen", return_value=response):
                    with self.assertRaises(RepositoryError):
                        repository.fetch_package_info("https://x.org", "a")


class TestDependencies(unittest.TestCase):
    """Выбор прямых зависимостей из метаданных."""

    def get(self, data):
        """Вызывает get_direct_dependencies с подменёнными метаданными."""
        with patch("dependencies.fetch_package_info", return_value=data):
            return dependencies.get_direct_dependencies("a", "https://x.org")

    def test_extras_and_duplicates_removed(self):
        """Extras пропускаются, повторы убираются, порядок сохраняется."""
        data = {"info": {"requires_dist": [
            "urllib3<3,>=1.21.1",
            "charset_normalizer<4,>=2",
            'PySocks>=1.5.6; extra == "socks"',
            'urllib3; python_version < "3"',
        ]}}
        self.assertEqual(self.get(data), ["urllib3", "charset-normalizer"])

    def test_no_dependencies(self):
        """requires_dist равный null даёт пустой список."""
        self.assertEqual(self.get({"info": {"requires_dist": None}}), [])

    def test_unexpected_format(self):
        """Неожиданная структура данных вызывает RepositoryError."""
        for data in [{}, {"info": {"requires_dist": "urllib3"}}]:
            with self.subTest(data=data):
                with self.assertRaises(RepositoryError):
                    self.get(data)

    def test_fetch_arguments(self):
        """Метаданные запрашиваются по заданным пакету и репозиторию."""
        with patch("dependencies.fetch_package_info") as fetch:
            fetch.return_value = {"info": {"requires_dist": None}}
            dependencies.get_direct_dependencies("req", "https://x.org")
        fetch.assert_called_once_with("https://x.org", "req")


class TestMain(unittest.TestCase):
    """Работа программы целиком (получение зависимостей подменяется)."""

    ARGS = ("--package", "requests", "--repo", "https://pypi.org/pypi")

    def test_prints_dependencies(self):
        """Зависимости выводятся по одной на строку."""
        with patch("main.get_direct_dependencies",
                   return_value=["idna", "urllib3"]):
            code, out, _ = run_main(*self.ARGS)
        self.assertEqual(code, 0)
        self.assertEqual(
            out, "Прямые зависимости пакета requests:\nidna\nurllib3\n")

    def test_no_dependencies(self):
        """Для пакета без зависимостей выводится сообщение."""
        with patch("main.get_direct_dependencies", return_value=[]):
            code, out, _ = run_main(*self.ARGS)
        self.assertEqual(code, 0)
        self.assertIn("нет прямых зависимостей", out)

    def test_repository_error(self):
        """Ошибка репозитория даёт сообщение и код 1."""
        error = RepositoryError("пакет не найден")
        with patch("main.get_direct_dependencies", side_effect=error):
            code, _, err = run_main(*self.ARGS)
        self.assertEqual(code, 1)
        self.assertIn("Ошибка: пакет не найден", err)

    def test_config_error(self):
        """Ошибка параметров даёт сообщение и код 1."""
        code, _, err = run_main()
        self.assertEqual(code, 1)
        self.assertIn("--package", err)


if __name__ == "__main__":
    unittest.main()
