import heapq
import math

def build_graph(edgeList, directed):
    """
    Build an adjacency list from a list of (u, v, weight) edges.
    Input: edgeList, directed flag.
    Output: dict vertex -> list of (neighbor, weight).
    Locals: graph, u, v, weight.
    """
    graph = {}
    for u, v, weight in edgeList:
        if u not in graph:
            graph[u] = []
        if v not in graph:
            graph[v] = []
        graph[u].append((v, weight))
        if not directed:
            graph[v].append((u, weight))
    return graph

def dijkstra(graph, source):
    """
    Single source shortest paths with non negative edge weights.
    Input: adjacency list graph, source vertex.
    Output: (dist, prev) maps from each vertex.
    Locals: dist, prev, heap, settled, distU, u, v, weight, candidate.
    """
    dist = {}
    prev = {}
    for vertex in graph:
        dist[vertex] = math.inf
        prev[vertex] = None
    if source not in graph:
        return dist, prev
    dist[source] = 0
    heap = [(0, source)]
    settled = set()
    while heap:
        distU, u = heapq.heappop(heap)
        if u in settled:
            continue
        settled.add(u)
        if distU > dist[u]:
            continue
        for v, weight in graph[u]:
            candidate = dist[u] + weight
            if candidate < dist[v]:
                dist[v] = candidate
                prev[v] = u
                heapq.heappush(heap, (candidate, v))
    return dist, prev

def reconstruct_path(prev, source, target):
    """
    Rebuild the shortest path from source to target using prev links.
    Input: prev map, source, target.
    Output: list of vertices or empty list if unreachable.
    Locals: path, current.
    """
    if target not in prev and target != source:
        return []
    path = []
    current = target
    while current is not None:
        path.append(current)
        if current == source:
            path.reverse()
            return path
        current = prev.get(current)
    return []

def format_dist(value):
    """
    Format a distance for printing, using inf for unreachable.
    Input: value.
    Output: string.
    Locals: none.
    """
    if value == math.inf:
        return "inf"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)

def print_result(label, graph, source, dist, prev):
    """
    Echo one Dijkstra run with distances and reconstructed paths.
    Input: label, graph, source, dist, prev.
    Output: none.
    Locals: vertex, pathText, path.
    """
    print(label)
    print(f"source: {source}")
    print(f"vertices: {sorted(graph.keys())}")
    for vertex in sorted(graph.keys()):
        path = reconstruct_path(prev, source, vertex)
        if dist[vertex] == math.inf:
            pathText = "unreachable"
        else:
            pathText = " -> ".join(str(x) for x in path)
        print(
            f"  to {vertex}: dist={format_dist(dist[vertex])}  "
            f"path={pathText}"
        )
    print()

def run_example(label, edgeList, source, directed, expected):
    """
    Run Dijkstra on one example and check expected distances.
    Input: label, edgeList, source, directed, expected dist map.
    Output: True if all expected distances match.
    Locals: graph, dist, prev, vertex, ok.
    """
    graph = build_graph(edgeList, directed)
    dist, prev = dijkstra(graph, source)
    print_result(label, graph, source, dist, prev)
    ok = True
    for vertex, want in expected.items():
        got = dist.get(vertex, math.inf)
        if got != want:
            print(f"FAIL {label}: vertex {vertex} got {got} want {want}")
            ok = False
    return ok

def example_classic_directed():
    """
    Classic small directed graph with a unique shortest tree.
    Input: none.
    Output: pass flag.
    Locals: edges, expected.
    """
    edges = [
        ("A", "B", 4),
        ("A", "C", 2),
        ("B", "C", 5),
        ("B", "D", 10),
        ("C", "E", 3),
        ("E", "D", 4),
        ("D", "F", 11),
    ]
    expected = {
        "A": 0,
        "B": 4,
        "C": 2,
        "D": 9,
        "E": 5,
        "F": 20,
    }
    return run_example(
        "Example 1 classic directed graph",
        edges,
        "A",
        True,
        expected,
    )

def example_undirected_mesh():
    """
    Undirected mesh where several routes compete.
    Input: none.
    Output: pass flag.
    Locals: edges, expected.
    """
    edges = [
        (0, 1, 7),
        (0, 2, 9),
        (0, 5, 14),
        (1, 2, 10),
        (1, 3, 15),
        (2, 3, 11),
        (2, 5, 2),
        (3, 4, 6),
        (4, 5, 9),
    ]
    expected = {
        0: 0,
        1: 7,
        2: 9,
        3: 20,
        4: 20,
        5: 11,
    }
    return run_example(
        "Example 2 undirected mesh",
        edges,
        0,
        False,
        expected,
    )

def example_unreachable():
    """
    Graph with a disconnected component that stays unreachable.
    Input: none.
    Output: pass flag.
    Locals: edges, expected.
    """
    edges = [
        ("S", "A", 1),
        ("A", "B", 2),
        ("X", "Y", 5),
    ]
    expected = {
        "S": 0,
        "A": 1,
        "B": 3,
        "X": math.inf,
        "Y": math.inf,
    }
    return run_example(
        "Example 3 disconnected component",
        edges,
        "S",
        True,
        expected,
    )

def example_single_vertex():
    """
    Trivial graph with only the source.
    Input: none.
    Output: pass flag.
    Locals: graph, dist, prev, ok.
    """
    graph = {"Z": []}
    dist, prev = dijkstra(graph, "Z")
    print_result("Example 4 single vertex", graph, "Z", dist, prev)
    ok = dist["Z"] == 0 and reconstruct_path(prev, "Z", "Z") == ["Z"]
    if not ok:
        print("FAIL Example 4 single vertex")
    return ok

def example_tie_break_paths():
    """
    Graph with equal cost alternatives, distances still unique.
    Input: none.
    Output: pass flag.
    Locals: edges, expected.
    """
    edges = [
        ("S", "U", 3),
        ("S", "V", 3),
        ("U", "T", 4),
        ("V", "T", 4),
        ("S", "T", 10),
    ]
    expected = {
        "S": 0,
        "U": 3,
        "V": 3,
        "T": 7,
    }
    return run_example(
        "Example 5 equal cost alternatives",
        edges,
        "S",
        True,
        expected,
    )

def main():
    """
    Run several Dijkstra examples and report pass or fail.
    Input: none.
    Output: printed distances and a final status line.
    Locals: checks, allOk.
    """
    checks = [
        example_classic_directed(),
        example_undirected_mesh(),
        example_unreachable(),
        example_single_vertex(),
        example_tie_break_paths(),
    ]
    allOk = all(checks)
    if allOk:
        print("all tests passed")
    else:
        print("some tests failed")
    return allOk

if __name__ == "__main__":
    main()