from typing import NamedTuple


class GraphResult(NamedTuple):
    """Результат обхода: граф и найденные циклы."""

    graph: dict
    cycles: list


def is_excluded(name, substring):
    """Проверяет, нужно ли пропустить пакет
    из-за фильтра (без учёта регистра)."""
    return bool(substring) and substring.lower() in name.lower()


def visible_dependencies(package, get_dependencies, substring):
    """Возвращает прямые зависимости пакета, кроме отфильтрованных."""
    dependencies = get_dependencies(package)
    return [name for name in dependencies
            if not is_excluded(name, substring)]


def build_graph(root, get_dependencies, substring=""):
    """
    Строит граф зависимостей пакета обходом в глубину (DFS без рекурсии).

    get_dependencies - функция «пакет -> список его прямых зависимостей».
    Пакеты, в имени которых есть substring, пропускаются.
    Возвращает GraphResult: словарь «пакет -> зависимости» в порядке обхода
    и список найденных циклов (каждый цикл - список имён по кругу).
    """
    graph = {root: visible_dependencies(root, get_dependencies, substring)}
    cycles = []
    path = [root]
    stack = [(root, iter(graph[root]))]
    while stack:
        _, children = stack[-1]
        child = next(children, None)
        if child is None:
            stack.pop()
            path.pop()
        elif child in path:
            cycles.append(path[path.index(child):] + [child])
        elif child not in graph:
            graph[child] = visible_dependencies(
                child, get_dependencies, substring)
            path.append(child)
            stack.append((child, iter(graph[child])))
    return GraphResult(graph, cycles)
