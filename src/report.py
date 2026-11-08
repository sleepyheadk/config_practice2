NO_DEPENDENCIES = "(нет зависимостей)"


def format_dependencies(names):
    """Превращает список зависимостей в строку для вывода."""
    return ", ".join(names) if names else NO_DEPENDENCIES


def format_graph(root, graph):
    """Возвращает строки со списком «пакет -> зависимости»."""
    lines = [f"Граф зависимостей пакета {root}:"]
    for package, dependencies in graph.items():
        lines.append(f"{package} -> {format_dependencies(dependencies)}")
    return lines


def format_cycles(cycles):
    """Возвращает строки с найденными циклическими зависимостями."""
    if not cycles:
        return ["Циклических зависимостей нет"]
    lines = ["Циклические зависимости:"]
    lines.extend(" -> ".join(cycle) for cycle in cycles)
    return lines


def format_report(root, result):
    """Собирает полный текст отчёта по результату обхода графа."""
    lines = format_graph(root, result.graph)
    lines.extend(format_cycles(result.cycles))
    return "\n".join(lines)
