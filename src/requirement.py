import re
from typing import NamedTuple

from errors import RepositoryError

NAME_PATTERN = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
EXTRAS_PATTERN = re.compile(r"^\s*\[[^\]]*\]")
EXTRA_MARKER_PATTERN = re.compile(r"\bextra\s*==")
SEPARATORS_PATTERN = re.compile(r"[-_.]+")


class Requirement(NamedTuple):
    """Разобранная строка зависимости."""

    name: str
    specifier: str
    marker: str


def normalize_name(name):
    """Приводит имя к единому виду: нижний регистр, разделители в '-'."""
    return SEPARATORS_PATTERN.sub("-", name).lower()


def clean_specifier(text):
    """Убирает из остатка строки extras, скобки и пробелы."""
    text = EXTRAS_PATTERN.sub("", text)
    return "".join(text.split()).strip("()")


def parse_requirement(line):
    """
    Разбирает строку зависимости формата PEP 508.

    Например: 'PySocks!=1.5.7,>=1.5.6; extra == "socks"'.
    Возвращает Requirement. Если имя не найдено, бросает RepositoryError.
    """
    body, _, marker = line.partition(";")
    match = NAME_PATTERN.match(body)
    if match is None:
        message = f"не удалось разобрать зависимость: {line!r}"
        raise RepositoryError(message)
    name = normalize_name(match.group(1))
    specifier = clean_specifier(body[match.end():])
    return Requirement(name, specifier, marker.strip())


def is_extra(requirement):
    """Проверяет, нужна ли зависимость только для extra-дополнения."""
    return EXTRA_MARKER_PATTERN.search(requirement.marker) is not None
