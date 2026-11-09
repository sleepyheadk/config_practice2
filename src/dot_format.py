INDENT = "    "
ROOT_STYLE = 'style=filled, fillcolor="#cfe2ff"'
CYCLE_STYLE = "color=red, penwidth=1.5"


def quote(name):
    """Заключает имя в кавычки и экранирует служебные символы DOT."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def closing_edges(cycles):
    """Возвращает множество рёбер, которые замыкают циклы."""
    return {(cycle[-2], cycle[-1]) for cycle in cycles}


def format_edge(source, target, closing):
    """Формирует строку ребра; ребро, замыкающее цикл, красное."""
    line = f"{INDENT}{quote(source)} -> {quote(target)}"
    if (source, target) in closing:
        line += f" [{CYCLE_STYLE}]"
    return line + ";"


def build_dot(root, graph, cycles=()):
    """
    Возвращает текст графа зависимостей на языке Graphviz (DOT).

    graph - словарь «пакет -> список прямых зависимостей», cycles - список
    найденных циклов (результат build_graph). Корневой пакет закрашен,
    рёбра, замыкающие циклы, выделены красным.
    """
    closing = closing_edges(cycles)
    lines = [
        f"digraph {quote(root)} {{",
        f"{INDENT}rankdir=TB;",
        f'{INDENT}node [shape=box, fontname="Helvetica"];',
        f"{INDENT}{quote(root)} [{ROOT_STYLE}];",
    ]
    for package, dependencies in graph.items():
        for dependency in dependencies:
            lines.append(format_edge(package, dependency, closing))
    lines.append("}")
    return "\n".join(lines) + "\n"
