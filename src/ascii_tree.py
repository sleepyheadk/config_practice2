BRANCH_MIDDLE = "|-- "
BRANCH_LAST = "`-- "
INDENT_MIDDLE = "|   "
INDENT_LAST = "    "
MARK_CYCLE = " (цикл)"
MARK_SEEN = " (см. выше)"


def pick_marker(package, path, expanded, graph):
    """Возвращает пометку для повтора пакета в дереве или пустую строку."""
    if package in path:
        return MARK_CYCLE
    if package in expanded and graph[package]:
        return MARK_SEEN
    return ""


def build_tree(root, graph):
    """
    Строит ASCII-дерево зависимостей и возвращает его текстом.

    graph - словарь «пакет -> список прямых зависимостей» (результат
    build_graph). Обход без рекурсии, с явным стеком. Зависимости
    пакета раскрываются только при первом появлении, повторы помечаются
    «(см. выше)», а замыкающие цикл пакеты - «(цикл)».
    """
    lines = [root]
    path = [root]
    expanded = {root}
    stack = [[graph[root], 0, ""]]
    while stack:
        frame = stack[-1]
        children, index, prefix = frame
        if index == len(children):
            stack.pop()
            path.pop()
            continue
        frame[1] += 1
        package = children[index]
        is_last = index == len(children) - 1
        marker = pick_marker(package, path, expanded, graph)
        branch = BRANCH_LAST if is_last else BRANCH_MIDDLE
        lines.append(prefix + branch + package + marker)
        if not marker:
            expanded.add(package)
            path.append(package)
            indent = INDENT_LAST if is_last else INDENT_MIDDLE
            stack.append([graph[package], 0, prefix + indent])
    return "\n".join(lines)
