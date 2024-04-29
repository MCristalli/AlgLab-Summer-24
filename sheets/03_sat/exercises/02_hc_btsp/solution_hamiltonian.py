from itertools import *
from typing import Optional, Any, Tuple, List

import networkx as nx
from pysat.solvers import Solver as SATSolver

class _EdgeVars:
    """
    The SAT-Solver API uses integers for variables, with negative integers for negations
    and zero for a false "dummy" variable. Shifting variable management to its own class
    can enhance code cleanliness and reduce errors.
    """
    Node = Any
    Edge = Tuple[Node, Node]

    def __init__(self, graph: nx.Graph, start=1) -> None:
        self._vars = {frozenset(edge): i for i, edge in enumerate(graph.edges, start=start)}
        self._reverse = {i: tuple(edge) for edge, i in self._vars.items()}

    def x(self, edge: Edge):
        """
        Return the variable representing the given edge.
        """
        return self._vars[frozenset(edge)]

    def edge(self, x: int) -> Tuple[Edge, bool]:
        """
        Return the edge represented by the given variable.
        The second return value indicates whether the edge is negated.
        """
        return (self._reverse[x], False) if x < 0 else (self._reverse[x], True)

    def not_x(self, edge: Edge):
        """
        Return the variable representing the negation of the given edge.
        """
        return -self.x(edge)

    def get_edge_selection(self, model: List[int]) -> List[Edge]:
        """
        Parse the selected edges from a given model (solution for a SAT-formula).
        """
        return [self.edge(x)[0] for x in model if x in self._reverse]


class HamiltonianCycleModel:
    def __init__(self, graph: nx.Graph) -> None:
        self.graph = graph
        # Decision Variable for each edge
        self.edge_vars = _EdgeVars(graph)
        self.solver = SATSolver("Minicard")

        # Setup initial constraints, since they will not change
        for node in self.graph.nodes:
            # at most 2 edges connected per node
            self.solver.add_atmost([self.edge_vars.x(edge) for edge in self.graph.edges(node)], 2)
            # at least 1 (incomming) edge per node
            self.solver.add_clause([self.edge_vars.x((u, v)) for (u, v) in self.graph.edges(node)])

            for incomming_edge in self.graph.edges(node):
                # for each incomming edge, that is selected, there exists an outgoing edge.
                self.solver.add_clause([self.edge_vars.not_x(incomming_edge)] + [self.edge_vars.x(edge) for edge in self.graph.edges(node) if edge != incomming_edge])

    def solve(self) -> Optional[List[Tuple[int, int]]]:
        """
        Solves the Hamiltonian Cycle Problem. If a HC is found,
        its edges are returned as a list.
        If the graph has no HC, 'None' is returned.
        """

        if not self.solver.solve():
            return None # A Hamiltonian Cycle doesnt exist
        #else:

        model = self.solver.get_model()
        assert model is not None

        subgraph_edges = self.edge_vars.get_edge_selection(model)
        subgraph = self.graph.edge_subgraph(subgraph_edges)


        while not nx.is_connected(subgraph):
            for component in nx.connected_components(subgraph):
                # for each component aka cycle, discard one edge
                self.solver.add_clause([self.edge_vars.not_x((u, v)) for (u, v) in subgraph.edges if u in component and v in component ])

            if self.solver.solve():
                model = self.solver.get_model()
                assert model is not None
                subgraph_edges = self.edge_vars.get_edge_selection(model)
                subgraph = self.graph.edge_subgraph(subgraph_edges)
            else:
                return None # A Hamiltonian Cycle doesnt exist

        return subgraph_edges
