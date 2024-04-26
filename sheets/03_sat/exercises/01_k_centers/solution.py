import math
from typing import Dict, Iterable, List

import networkx as nx
from pysat.solvers import Solver as SATSolver

import operator



class KCentersSolver:
    def __init__(self, graph: nx.Graph) -> None:
        """
        Creates a solver for the k-centers problem on the given networkx graph.
        The graph is not necessarily complete, so not all nodes are neighbors.
        The distance between two neighboring nodes is a numeric value (int / float), saved as
        an edge data parameter called "weight".
        There are multiple ways to access this data, and networkx also implements
        several algorithms that automatically make use of this value.
        Check the networkx documentation for more information!
        """
        self.centers = None
        self.sat = None
        self.length = None
        self.upperbound = None
        self.graph = graph
        self.vars = {node: i for i, node in enumerate(graph.nodes)}
        self.stop = False

    def solve_heur(self, k: int) -> List[int]:
        """
        Calculate a heuristic solution to the k-centers problem.
        Returns the k selected centers as a list of ints.
        (nodes will be ints in the given graph).
        """
        centers = []

        nodes = nx.algorithms.centrality.betweenness.betweenness_centrality(self.graph, weight="weight")

        for i in range(k):
            key, value = max(nodes.items(), key=lambda x: x[1])
            centers.append(key)
            del nodes[key]

        print(centers)
        return centers

    def calculate_bottleneck(self, centers) -> float:
        apsp = dict(nx.all_pairs_dijkstra_path_length(self.graph))
        bottleneck_distance = max(min(apsp[u][c] for c in centers) for u in self.graph.nodes)
        return bottleneck_distance

    def calculate_sat(self, k: int) -> List[int]:
        # delete node pairs that are too far from each other
        for node1 in self.graph.nodes:
            for node2 in self.graph.nodes:
                if node2 in self.length[node1]:
                    if self.length[node1][node2] >= self.upperbound:
                        del self.length[node1][node2]

        # add conditions to SAT Solver
        for node in self.graph.nodes:
            self.sat.add_clause(self.length[node].keys())

        self.sat.add_atmost(self.graph.nodes, k)

        if self.sat.solve():
            # set new upperbound
            centers = []
            solution = self.sat.get_model()
            for i in solution:
                if i > 0:
                    centers.append(i)

            self.upperbound = self.calculate_bottleneck(centers)
            self.centers = centers
        else:
            self.stop = True

    def solve(self, k: int) -> List[int]:
        """
        For the given parameter k, calculate the optimal solution
        to the k-centers solution and return the selected centers as a list.
        """
        self.sat = SATSolver("MiniCard")
        # get heuristic upperbound
        self.centers = self.solve_heur(k)

        self.upperbound = self.calculate_bottleneck(self.centers)

        # get all shortest paths between nodes
        self.length = dict(nx.all_pairs_dijkstra_path_length(self.graph))

        while not self.stop:
            self.calculate_sat(k)

        return self.centers
