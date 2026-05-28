from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from or_model.cost_matrix import ProblemInstance


@dataclass
class TSPResult:
    """Visit order over node indices in the routing graph."""

    order: list[int]
    objective_cost: float
    method: str


def solve_tsp(problem: ProblemInstance) -> TSPResult:
    """Solve open TSP: start at node 0, visit all attractions, end at last node."""
    n = len(problem.labels)
    if n <= 2:
        return TSPResult(order=list(range(n)), objective_cost=0.0, method="trivial")

    start = 0
    end = n - 1
    middle = list(range(1, end))

    if len(middle) <= 8:
        return _solve_exact(problem.cost_matrix, start, middle, end)

    return _solve_heuristic(problem.cost_matrix, start, middle, end)


def _path_cost(matrix: np.ndarray, order: list[int]) -> float:
    return float(sum(matrix[order[i], order[i + 1]] for i in range(len(order) - 1)))


def _solve_exact(
    matrix: np.ndarray, start: int, middle: list[int], end: int
) -> TSPResult:
    best_order: list[int] | None = None
    best_cost = float("inf")

    for perm in itertools.permutations(middle):
        order = [start, *perm, end]
        cost = _path_cost(matrix, order)
        if cost < best_cost:
            best_cost = cost
            best_order = list(order)

    assert best_order is not None
    return TSPResult(order=best_order, objective_cost=best_cost, method="exact")


def _solve_heuristic(
    matrix: np.ndarray, start: int, middle: list[int], end: int
) -> TSPResult:
    remaining = set(middle)
    order = [start]
    current = start

    while remaining:
        nxt = min(remaining, key=lambda node: matrix[current, node])
        remaining.remove(nxt)
        order.append(nxt)
        current = nxt

    order.append(end)
    order = _two_opt(matrix, order)
    return TSPResult(
        order=order,
        objective_cost=_path_cost(matrix, order),
        method="nearest_neighbor+2opt",
    )


def _two_opt(matrix: np.ndarray, order: list[int]) -> list[int]:
    """2-opt improvement keeping first and last node fixed."""
    improved = True
    best = order[:]
    best_cost = _path_cost(matrix, best)

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                cost = _path_cost(matrix, candidate)
                if cost + 1e-9 < best_cost:
                    best = candidate
                    best_cost = cost
                    improved = True
                    break
            if improved:
                break

    return best
