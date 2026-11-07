import argparse


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
