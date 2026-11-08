import sys

from cli import parse_args
from dependencies import make_source
from errors import ConfigError, RepositoryError
from graph import build_graph
from report import format_report
from validation import validate_args


def run(args):
    """Строит граф зависимостей пакета и выводит его на экран."""
    root, get_dependencies = make_source(
        args.package, args.repo, args.test_mode)
    result = build_graph(root, get_dependencies, args.filter)
    print(format_report(root, result))


def main():
    """Точка входа в программу"""
    args = parse_args()
    try:
        validate_args(args)
        run(args)
    except (ConfigError, RepositoryError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
