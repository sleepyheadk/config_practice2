from functools import partial

from errors import RepositoryError
from file_repository import make_file_provider
from repository import fetch_package_info
from requirement import is_extra, normalize_name, parse_requirement


def extract_requirement_lines(data):
    """
    Достаёт из метаданных пакета список строк зависимостей.

    Если у пакета нет зависимостей, возвращает пустой список.
    Если формат данных неожиданный, бросает RepositoryError.
    """
    package_info = data.get("info")
    if not isinstance(package_info, dict):
        raise RepositoryError("в ответе репозитория нет данных о пакете")
    lines = package_info.get("requires_dist") or []
    if not isinstance(lines, list):
        raise RepositoryError("неожиданный формат списка зависимостей")
    if not all(isinstance(line, str) for line in lines):
        raise RepositoryError("неожиданный формат списка зависимостей")
    return lines


def get_direct_dependencies(package, repo):
    """
    Возвращает имена прямых зависимостей пакета.

    Зависимости, нужные только для extra-дополнений, пропускаются.
    Имена нормализованы, повторы убраны, порядок сохранён.
    """
    data = fetch_package_info(repo, package)
    lines = extract_requirement_lines(data)
    requirements = [parse_requirement(line) for line in lines]
    names = [req.name for req in requirements if not is_extra(req)]
    return list(dict.fromkeys(names))


def make_source(package, repo, test_mode):
    """
    Выбирает источник данных о зависимостях.

    Возвращает имя корневого пакета и функцию
    «пакет -> список его прямых зависимостей».
    """
    if test_mode:
        return package, make_file_provider(repo)
    return normalize_name(package), partial(get_direct_dependencies, repo=repo)
