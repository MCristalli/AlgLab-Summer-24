import logging
import math
from enum import Enum
from typing import List, Optional, Tuple

import networkx as nx
from _timer import Timer
from solution_hamiltonian import HamiltonianCycleModel


class SearchStrategy(Enum):
    """
    Different search strategies for the solver.
    """

    SEQUENTIAL_UP = 1  # Try smallest possible k first.
    SEQUENTIAL_DOWN = 2  # Try any improvement.
    BINARY_SEARCH = 3  # Try a binary search for the optimal k.

    def __str__(self):
        return self.name.title()

    @staticmethod
    def from_str(s: str):
        return SearchStrategy[s.upper()]


class BottleneckTSPSolver:
    def __init__(self, graph: nx.Graph, logger: Optional[logging.Logger] = None) -> None:
        """
        Creates a solver for the Bottleneck Traveling Salesman Problem on the given networkx graph.
        You can assume that the input graph is complete, so all nodes are neighbors.
        The distance between two neighboring nodes is a numeric value (int / float), saved as
        an edge data parameter called "weight".
        There are multiple ways to access this data, and networkx also implements
        several algorithms that automatically make use of this value.
        Check the networkx documentation for more information!
        """
        self._logger = logger or logging.getLogger("BottleneckTSP-Optimizer")
        self.graph = graph
        self.lower_bound = min(weight for (u, v, weight) in self.graph.edges(data="weight"))
        self.upper_bound = max(weight for (u, v, weight) in self.graph.edges(data="weight"))
        self.best_solution = None

    def _add_solution(self, solution: List):
        # find the next largest edge, less than upper_bound
        largest_edge = max(self.graph.edges[edge]["weight"] for edge in solution)
        next_upper_bound = max(weight for (u, v, weight) in self.graph.edges(data="weight") if weight < largest_edge)
        if next_upper_bound < self.upper_bound:
            self._logger.info(f"A solution of size {largest_edge:.4f} was found!")
            self.upper_bound = next_upper_bound
            self.best_solution = solution

    def _set_lower_bound(self, lower_bound: int):
        if lower_bound > self.lower_bound:
            self._logger.info(f"Increased lower bound to {lower_bound:.4f}.")
        self.lower_bound = max(self.lower_bound, lower_bound)

    def _get_next_t(self, search_strategy: SearchStrategy) -> int:
        # The next k to try.
        if search_strategy == SearchStrategy.SEQUENTIAL_UP:
            # Try the smallest possible k.
            t = self.lower_bound
        elif search_strategy == SearchStrategy.SEQUENTIAL_DOWN:
            # Try the smallest possible improvement.
            t = self.upper_bound
        elif search_strategy == SearchStrategy.BINARY_SEARCH:
            # Try a binary search
            t = (self.lower_bound + self.upper_bound) / 2
        else:
            msg = "Invalid search strategy!"
            raise ValueError(msg)
        assert self.lower_bound <= t <= self.upper_bound
        return t

    def optimize_bottleneck(
        self,
        time_limit: float = math.inf,
        search_strategy: SearchStrategy = SearchStrategy.BINARY_SEARCH,
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Find the optimal bottleneck tsp tour.
        """
        self.timer = Timer(time_limit)
        try:
            while self.lower_bound < self.upper_bound:
                self.timer.check()  # throws TimeoutError if time is up

                t = self._get_next_t(search_strategy)
                subgraph = self.graph.edge_subgraph([(u, v) for (u, v, weight) in self.graph.edges(data="weight") if weight <= t ])

                if subgraph.number_of_edges() < subgraph.number_of_nodes():
                    # if there are not enough edges to form a cycle, break
                    break

                t_bounded_hc = HamiltonianCycleModel(subgraph).solve(self.timer.remaining())
                if t_bounded_hc is None:  # No Solution!
                    # find the next smallest edge
                    next_lower_bound = min(weight for (u, v, weight) in self.graph.edges(data="weight") if weight > t)
                    assert next_lower_bound > self.lower_bound
                    self._set_lower_bound(next_lower_bound)
                else:  # New solution found!
                    self._add_solution(t_bounded_hc)
        except TimeoutError:
            self._logger.info("Timeout reached.")

        return self.best_solution
