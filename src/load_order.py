def build_load_order(root, graph):
    """
    Возвращает порядок загрузки пакетов: зависимости раньше зависящих.

    graph - словарь «пакет -> список прямых зависимостей» (результат
    build_graph). Обход в глубину без рекурсии: пакет записывается
    в результат после всех своих зависимостей, корень идёт последним.
    Рёбра, замыкающие цикл, пропускаются.
    """
    order = []
    visited = {root}
    stack = [(root, iter(graph[root]))]
    while stack:
        package, children = stack[-1]
        child = next(children, None)
        if child is None:
            order.append(package)
            stack.pop()
        elif child not in visited:
            visited.add(child)
            stack.append((child, iter(graph[child])))
    return order
