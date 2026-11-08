NO_DEPENDENCIES = "(нет зависимостей)"
CYCLE_WARNING = ("Внимание: в графе есть циклические зависимости, "
                 "порядок для входящих в них пакетов условный:")


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


def format_order(order):
    """Возвращает пронумерованный список пакетов в порядке загрузки."""
    return [f"{number}. {name}" for number, name in enumerate(order, start=1)]


def format_load_order(root, order, cycles):
    """Собирает текст с порядком загрузки зависимостей пакета."""
    lines = [f"Порядок загрузки зависимостей пакета {root}:"]
    lines.extend(format_order(order))
    if cycles:
        lines.append(CYCLE_WARNING)
        lines.extend(" -> ".join(cycle) for cycle in cycles)
    return "\n".join(lines)
