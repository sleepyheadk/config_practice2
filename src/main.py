import argparse
import re
import os
from urllib.parse import urlparse
import sys

PACKAGE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")


def parse_args():
    """
    Разбирает аргументы командной строки.

    Возвращает объект с параметрами,
    заданными пользователем.
    """
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей pip-пакетов"
    )

    parser.add_argument(
        "--package",
        help="имя анализируемого пакета"
    )
    parser.add_argument(
        "--repo",
        help="URL-адрес репозитория или путь к файлу тестового репозитория"
    )
    parser.add_argument(
        "--test-mode", action="store_true",
        help="считать --repo путём к файлу тестового репозитория"
    )
    parser.add_argument(
        "--output", default="graph.svg",
        help="имя файла с изображением графа (по умолчанию graph.svg)",
    )
    parser.add_argument(
        "--ascii-tree", action="store_true",
        help="вывести зависимости в виде ASCII-дерева"
    )
    parser.add_argument(
        "--filter", default="",
        help="исключить пакеты, в имени которых есть эта подстрока"
    )
    return parser.parse_args()


class ConfigError(Exception):
    """Ошибка в параметрах, заданных пользователем"""


def validate_package(name):
    """Проверяет имя пакета"""
    if name is None:
        raise ConfigError("имя пакета не задано (--package)")
    if not name.strip():
        raise ConfigError("имя пакета не может быть пустым")
    if not re.match(PACKAGE_NAME_PATTERN, name):
        raise ConfigError("недопустимое имя пакета")


def validate_repo(repo, test_mode):
    """Проверяет репозиторий"""
    if repo is None:
        raise ConfigError("репозиторий не задан (--repo)")
    if not repo.strip():
        raise ConfigError("имя репозитория не может быть пустым")
    if test_mode:
        if not os.path.exists(repo):
            raise ConfigError("файл не найден")
        if not os.path.isfile(repo):
            raise ConfigError(f"{repo} не является файлом")
    else:
        parsed = urlparse(repo)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ConfigError(f"некорректный URL: {repo}")


def validate_output(output):
    """Проверяет имя выходного файла"""
    if not output.strip():
        raise ConfigError("имя выходного файла не может быть пустым")
    if not output.lower().endswith(".svg"):
        raise ConfigError("выходной файл должен иметь расширение .svg")
    folder = os.path.dirname(output)
    if folder and not os.path.isdir(folder):
        raise ConfigError(f"папка не существует: '{folder}'")
    if os.path.isdir(output):
        raise ConfigError(f"'{output}' является папкой, а не файлом")


def validate_args(args):
    """Проверяет все параметры"""
    validate_package(args.package)
    validate_repo(args.repo, args.test_mode)
    validate_output(args.output)


def main():
    """Точка входа в программу"""
    args = parse_args()
    try:
        validate_args(args)
    except ConfigError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)
    for key, value in vars(args).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
