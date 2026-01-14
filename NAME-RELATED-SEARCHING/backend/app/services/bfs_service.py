from collections import deque
from typing import Callable, List, Optional
from neighbor_wikidata import get_neighbors
from normalize import normalize_name

def find_path(start : str, 
              target : str, 
              get_neighbors : Callable[[str], List[str]], 
              max_depth : int
              ) -> Optional[List[str]] :
    
    queue = deque([(start, [start], 0)])
    visited = set([start])

    while queue:
        current, path, depth = queue.popleft()
        print(f"[BFS] Visiting {current}, depth={depth}")

        if current == target:
            return path

        if depth >= max_depth:
            continue

        try:
            neighbors = get_neighbors(current)
        except Exception as e:
            print(f"[WARN] Failed to get neighbors of {current}: {e}")
            continue

        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor], depth + 1))

    return None

# test
# def find_path_by_name(
#     from_name: str,
#     to_name: str,
#     max_depth: int = 3,
# ):
#     """
#     Normalize name -> try BFS with each candidate
#     """

#     print(f"\nNormalizing FROM name: {from_name}")
#     from_candidates = normalize_name(from_name, limit=5)

#     print(f"Normalizing TO name: {to_name}")
#     to_candidates = normalize_name(to_name, limit=5)

#     if not from_candidates or not to_candidates:
#         print("No candidates found")
#         return None

#     # thử từng cặp candidate
#     for f in from_candidates:
#         for t in to_candidates:
#             print(
#                 f"\nTrying BFS: {f['label']} ({f['qid']}) "
#                 f"→ {t['label']} ({t['qid']})"
#             )

#             path = find_path(
#                 start=f["qid"],
#                 target=t["qid"],
#                 get_neighbors=get_neighbors,
#                 max_depth=max_depth,
#             )

#             if path:
#                 return {
#                     "from": f,
#                     "to": t,
#                     "path": path,
#                 }

#     return None


# if __name__ == "__main__":
#     result = find_path_by_name(
#         from_name="Elon Musk",
#         to_name="Donald Trump",
#         max_depth=2,
#     )

#     if result:
#         print("\nFOUND PATH 🎉")
#         print("From:", result["from"]["label"])
#         print("To:", result["to"]["label"])
#         print("Path:", " -> ".join(result["path"]))
#     else:
#         print("\nNO PATH FOUND")