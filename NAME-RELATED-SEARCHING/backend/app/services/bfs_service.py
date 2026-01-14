from collections import deque

def find_path(start, target, get_neighbors, max_depth=4):
    queue = deque([(start, [start], 0)])
    visited = set([start])

    while queue:
        current, path, depth = queue.popleft()

        if current == target:
            return path

        if depth >= max_depth:
            continue

        for neighbor in get_neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor], depth + 1))

    return None
