import http.client
import json
import urllib.error
import urllib.request

from errors import RepositoryError

TIMEOUT_SECONDS = 10
HTTP_NOT_FOUND = 404


def build_url(repo, package):
    """Формирует адрес метаданных пакета: <repo>/<package>/json"""
    return f"{repo.rstrip('/')}/{package}/json"


def describe_http_error(error, url):
    """Возвращает понятное описание ошибки, которую вернул сервер."""
    if error.code == HTTP_NOT_FOUND:
        return f"пакет не найден в репозитории ({url})"
    return f"сервер вернул ошибку {error.code} ({url})"


def download(url):
    """Скачивает содержимое по адресу и возвращает его как bytes."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise RepositoryError(describe_http_error(error, url)) from error
    except (OSError, ValueError, http.client.HTTPException) as error:
        reason = getattr(error, "reason", error)
        message = f"не удалось подключиться к {url}: {reason}"
        raise RepositoryError(message) from error


def parse_json(body, url):
    """Преобразует ответ сервера в словарь."""
    try:
        data = json.loads(body)
    except ValueError as error:
        message = f"ответ сервера не является JSON ({url})"
        raise RepositoryError(message) from error
    if not isinstance(data, dict):
        raise RepositoryError(f"неожиданный формат ответа ({url})")
    return data


def fetch_package_info(repo, package):
    """
    Скачивает метаданные пакета из репозитория.

    Возвращает словарь с данными пакета. При любой проблеме
    (нет сети, пакет не найден, плохой ответ) бросает RepositoryError.
    """
    url = build_url(repo, package)
    return parse_json(download(url), url)
