import re

from errors import RepositoryError

NAME_PATTERN = re.compile(r"[A-Z]+")
COMMENT_MARK = "#"


def parse_line(line, number):
    """
    Разбирает строку описания пакета вида 'A: B C'.

    Возвращает имя пакета и список его зависимостей без повторов.
    """
    name, separator, rest = line.partition(":")
    if not separator:
        message = f"строка {number}: ожидается формат 'A: B C'"
        raise RepositoryError(message)
    name = name.strip()
    dependencies = rest.split()
    for item in [name, *dependencies]:
        if not NAME_PATTERN.fullmatch(item):
            message = (f"строка {number}: недопустимое имя {item!r}, "
                       "нужны большие латинские буквы")
            raise RepositoryError(message)
    return name, list(dict.fromkeys(dependencies))


def parse_repository(text):
    """
    Разбирает текст тестового репозитория.

    Возвращает словарь «пакет -> список прямых зависимостей».
    Пустые строки и комментарии (после #) игнорируются.
    """
    graph = {}
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split(COMMENT_MARK)[0].strip()
        if not line:
            continue
        name, dependencies = parse_line(line, number)
        if name in graph:
            raise RepositoryError(f"строка {number}: пакет {name} уже описан")
        graph[name] = dependencies
    if not graph:
        raise RepositoryError("тестовый репозиторий пуст")
    return graph


def read_file(path):
    """Читает текстовый файл тестового репозитория."""
    try:
        with open(path, encoding="utf-8-sig") as file:
            return file.read()
    except (OSError, UnicodeDecodeError) as error:
        message = f"не удалось прочитать файл {path}: {error}"
        raise RepositoryError(message) from error


def make_lookup(graph):
    """Возвращает функцию «пакет -> список его прямых зависимостей»."""
    known = set(graph)
    for dependencies in graph.values():
        known.update(dependencies)

    def lookup(package):
        if package not in known:
            message = f"пакет {package} не найден в тестовом репозитории"
            raise RepositoryError(message)
        return list(graph.get(package, []))

    return lookup


def make_file_provider(path):
    """
    Читает тестовый репозиторий из файла.

    Возвращает функцию «пакет -> список его прямых зависимостей».
    """
    return make_lookup(parse_repository(read_file(path)))
