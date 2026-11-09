import sys

from ascii_tree import build_tree
from cli import parse_args
from dependencies import make_source
from dot_format import build_dot
from errors import ConfigError, RenderError, RepositoryError
from graph import build_graph
from load_order import build_load_order
from render import save_graph
from report import format_load_order
from validation import validate_args


def visualize(root, result, args):
    """Выводит ASCII-дерево (если задано) и сохраняет граф в файлы."""
    if args.ascii_tree:
        print(build_tree(root, result.graph))
        print()
    dot_text = build_dot(root, result.graph, result.cycles)
    dot_path = save_graph(dot_text, args.output)
    print(f"Граф сохранён: {args.output}")
    print(f"Текст на языке DOT: {dot_path}")


def run(args):
    """Строит граф зависимостей пакета и выводит результат."""
    root, get_dependencies = make_source(
        args.package, args.repo, args.test_mode)
    result = build_graph(root, get_dependencies, args.filter)
    if args.load_order:
        order = build_load_order(root, result.graph)
        print(format_load_order(root, order, result.cycles))
    else:
        visualize(root, result, args)


def main():
    """Точка входа в программу"""
    args = parse_args()
    try:
        validate_args(args)
        run(args)
    except (ConfigError, RepositoryError, RenderError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
