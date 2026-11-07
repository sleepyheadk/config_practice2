import sys

from cli import parse_args
from dependencies import get_direct_dependencies
from errors import ConfigError, RepositoryError
from validation import validate_args


def print_dependencies(package, dependencies):
    """Выводит прямые зависимости пакета на экран."""
    if not dependencies:
        print(f"У пакета {package} нет прямых зависимостей")
        return
    print(f"Прямые зависимости пакета {package}:")
    for name in dependencies:
        print(name)


def run(args):
    """Получает и выводит прямые зависимости пакета."""
    if args.test_mode:
        raise ConfigError("тестовый режим пока не реализован")
    dependencies = get_direct_dependencies(args.package, args.repo)
    print_dependencies(args.package, dependencies)


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
