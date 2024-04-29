import logging
import math
from typing import Optional, Dict, Iterable, List, Set, Any, Tuple

import networkx as nx
from pysat.solvers import Solver as SATSolver

class _NodeVars:
    """
    The SAT-Solver API uses integers for variables, with negative integers for negations
    and zero for a false "dummy" variable. Shifting variable management to its own class
    can enhance code cleanliness and reduce errors.
    """
    Node = Any
    Edge = Tuple[Node, Node]

    def __init__(self, graph: nx.Graph, start=1) -> None:
        self._vars = {node: i for i, node in enumerate(graph.nodes, start=start)}
        self._reverse = {i: node for node, i in self._vars.items()}

    def x(self, node: Node):
        """
        Return the variable representing the given node.
        """
        return self._vars[node]

    def node(self, x: int) -> Tuple[Node, bool]:
        """
        Return the node represented by the given variable.
        The second return value indicates whether the node is negated.
        """
        return (self._reverse[x], False) if x < 0 else (self._reverse[x], True)

    def not_x(self, node: Node):
        """
        Return the variable representing the negation of the given node.
        """
        return -self.x(node)

    def get_node_selection(self, model: List[int]) -> List[Node]:
        """
        Parse the selected nodes from a given model (solution for a SAT-formula).
        """
        return [self.node(x)[0] for x in model if x in self._reverse]



class KCentersSolver:
    def __init__(self, graph: nx.Graph, logger: Optional[logging.Logger] = None) -> None:
        """
        Creates a solver for the k-centers problem on the given networkx graph.
        The graph is not necessarily complete, so not all nodes are neighbors.
        The distance between two neighboring nodes is a numeric value (int / float), saved as
        an edge data parameter called "weight".
        There are multiple ways to access this data, and networkx also implements
        several algorithms that automatically make use of this value.
        Check the networkx documentation for more information!
        """
        self._logger = logger or logging.getLogger("KCenters-Solver")
        self.graph = graph
        self.node_vars = _NodeVars(graph)
        self.centers = list()
        self.apsp = dict(nx.all_pairs_dijkstra_path_length(self.graph)) # all pairs weighted shortest paths

    def solve_heur(self, k: int) -> List[int]:
        """
        Calculate a heuristic solution to the k-centers problem.
        Returns the k selected centers as a list of ints.
        (nodes will be ints in the given graph).
        """
        # Generate the Minimum Spanning Tree
        subgraph = nx.minimum_spanning_tree(self.graph)
        spanning_edges = list(subgraph.edges.data()) # edges with data
        spanning_edges.sort(
            key=lambda x: x[2]["weight"],
            reverse=True,
        )
        # remove at most k - 1 edges to get k connected components.
        edges_to_remove = k - nx.number_connected_components(subgraph)
        subgraph.remove_edges_from(spanning_edges[:edges_to_remove])
        assert nx.number_connected_components(subgraph) == k

        # Finds the centers for each subgraph induced by the connected components nodes.
        centers = [nx.center(subgraph.subgraph(component), weight="weight")[0] for component in nx.connected_components(subgraph)]
        return centers

    def _bottleneck_distance(self, centers: List[int]):
        return max(min(self.apsp[u][c] for c in centers) for u in self.graph.nodes)

    def solve(self, k: int) -> List[int]:
        """
        For the given parameter k, calculate the optimal solution
        to the k-centers solution and return the selected centers as a list.
        """
        sat = SATSolver("MiniCard")
        self.centers = self.solve_heur(k)
        self.upper_bound = self._bottleneck_distance(self.centers)

        # each variable represents a node.
        # at most k centers can be selectes.
        sat.add_atmost([self.node_vars.x(v) for v in self.graph.nodes], k)

        while True:
            # Each node has a distributtion radius. All nodes need to be covered by at least one radius.
            # For each nodes find all nodes in the distribution radius, and add a clause to slect at elast 1 node for that radius
            nodes_inside_radius = {u: [v for (v, length) in lengths.items() if length < self.upper_bound] for (u, lengths) in self.apsp.items() }
            for (u, inside_radius) in nodes_inside_radius.items():
                # Select one node, to cover each radius
                sat.add_clause([self.node_vars.x(v) for v in inside_radius])

            if sat.solve():
                # we found a solution!
                model = sat.get_model()
                assert model is not None
                self.centers = self.node_vars.get_node_selection(model)

                new_upper_bound = self._bottleneck_distance(self.centers)
                assert new_upper_bound < self.upper_bound
                self.upper_bound = new_upper_bound

                self._logger.info(f"Decreased upper bound to {self.upper_bound:.4f}.")
            else:
                # There exists no solution!
                break

        self._logger.info(f"Optimum reached, with size {self.upper_bound:.4f}!")

        return self.centers
