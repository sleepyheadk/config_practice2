import os
import subprocess

from errors import RenderError

DOT_COMMAND = "dot"
TIMEOUT_SECONDS = 60
ENCODING = "utf-8"


def dot_file_path(output):
    """Возвращает путь к DOT-файлу рядом с SVG: graph.svg -> graph.dot"""
    return os.path.splitext(output)[0] + ".dot"


def write_text(path, text):
    """Записывает текст в файл, ошибки записи превращает в RenderError."""
    try:
        with open(path, "w", encoding=ENCODING) as file:
            file.write(text)
    except OSError as error:
        message = f"не удалось записать файл {path}: {error}"
        raise RenderError(message) from error


def run_dot(dot_text):
    """Запускает Graphviz и возвращает текст SVG-изображения."""
    try:
        result = subprocess.run(
            [DOT_COMMAND, "-Tsvg"], input=dot_text, capture_output=True,
            text=True, encoding=ENCODING, timeout=TIMEOUT_SECONDS)
    except FileNotFoundError as error:
        message = ("Graphviz не найден: установите его и добавьте "
                   f"команду {DOT_COMMAND} в PATH")
        raise RenderError(message) from error
    except subprocess.TimeoutExpired as error:
        message = f"Graphviz не ответил за {TIMEOUT_SECONDS} секунд"
        raise RenderError(message) from error
    except OSError as error:
        message = f"не удалось запустить Graphviz: {error}"
        raise RenderError(message) from error
    if result.returncode != 0:
        message = f"Graphviz завершился с ошибкой: {result.stderr.strip()}"
        raise RenderError(message)
    return result.stdout


def save_graph(dot_text, output):
    """
    Сохраняет граф в файлах: DOT рядом с SVG и само изображение.

    Сначала записывается DOT-файл (он остаётся, даже если Graphviz
    недоступен), затем Graphviz рисует SVG. Возвращает путь к DOT-файлу.
    """
    dot_path = dot_file_path(output)
    write_text(dot_path, dot_text)
    write_text(output, run_dot(dot_text))
    return dot_path
