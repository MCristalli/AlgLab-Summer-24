"""
Implement the Dantzig-Fulkerson-Johnson formulation for the TSP.
"""

import typing

import gurobipy as gp
import networkx as nx


class _EdgeVariables:
    """
    A helper class that manages the variables for the edges.
    Such a helper class turns out to be useful in many cases.
    """
    EPSILON = 0.01 # if the weight of an edge exceeds this value it is considered selected.

    def __init__(self, G: nx.Graph, model: gp.Model):
        self._graph = G
        self._model = model
        self._vars = {
            (u, v): model.addVar(vtype=gp.GRB.CONTINUOUS, name=f"edge_{u}_{v}", lb=0, ub=1)
            for u, v in G.edges
        }

    def x(self, v, w) -> gp.Var:
        """
        Return variable for edge (v, w).
        """
        if (v, w) in self._vars:
            return self._vars[v, w]
        # If (v,w) was not found, try (w,v)
        return self._vars[w, v]

    def outgoing_edges(self, vertices):
        """
        Return all edges&variables that are outgoing from the given vertices.
        """
        # Not super efficient, but efficient enough for our purposes.
        for (v, w), x in self._vars.items():
            if v in vertices and w not in vertices:
                yield (v, w), x
            elif w in vertices and v not in vertices:
                yield (w, v), x

    def incident_edges(self, v):
        """
        Return all edges&variables that are incident to the given vertex.
        """
        for n in self._graph.neighbors(v):
            yield (v, n), self.x(v, n)

    def __iter__(self):
        """
        Iterate over all edges&variables.
        """
        return iter(self._vars.items())

    def as_graph(self, in_callback: bool = False):
        """
        Return the current solution as a graph.
        """
        if in_callback:
            # If we are in a callback, we need to use the solution from the callback.
            used_edges = [(*vw, {"x": x.X}) for vw, x in self if self._model.cbGetSolution(x) >= self.EPSILON]
        else:
            # Otherwise, we can use the solution from the model.
            used_edges = [(*vw, {"x": x.X}) for vw, x in self if x.X >= self.EPSILON]
        return nx.Graph(used_edges)


class GurobiTspRelaxationSolver:
    """
    A TSP Relaxation Solver in Gurobi
    """

    def __init__(self, G: nx.Graph):
        """
        G is a weighted networkx graph, where the weight of an edge is stored in the
        "weight" attribute. It is strictly positive.
        """
        self.graph = G
        assert (
            G.number_of_edges() == G.number_of_nodes() * (G.number_of_nodes() - 1) / 2
        ), "Invalid graph"
        assert all(
            weight > 0 for _, _, weight in G.edges.data("weight", default=None)
        ), "Invalid graph"
        self._model = gp.Model()
        self._edge_vars = _EdgeVariables(self.graph, self._model)
        self._constarint_two_incident_edges_per_node()
        self._minimize_cycle_length()

    def _constarint_two_incident_edges_per_node(self):
        for u in self.graph.nodes:
            self._model.addConstr(sum(x for _, x in self._edge_vars.incident_edges(u)) == 2)

    def _minimize_cycle_length(self):
        self._model.setObjective(sum(self.graph.edges[edge]["weight"] * x for edge, x in self._edge_vars), gp.GRB.MINIMIZE)

    def get_lower_bound(self) -> float:
        """
        Return the current lower bound.
        """
        # Only works if the model has been optimized once.
        return self.model.ObjBound

    def get_solution(self) -> typing.Optional[nx.Graph]:
        """
        Return the current solution as a graph.

        The solution should be a networkx Graph were the
        fractional value of the edge is stored in the "x" attribute.
        You do not have to add edges with x=0.

        ```python
        graph = nx.Graph()
        graph.add_edge(0, 1, x=0.5)
        graph.add_edge(1, 2, x=1.0)
        ```
        """
        # Only try to get a solution, if the model has been solved optimally
        assert self._model.status == gp.GRB.OPTIMAL
        solution_graph = self._edge_vars.as_graph()
        return solution_graph

    def get_objective(self) -> typing.Optional[float]:
        """
        Return the objective value of the last solution.
        """
        # Only works if the model has been optimized once.
        return self._model.ObjVal

    def solve(self) -> None:
        """
        Solve the model and return the objective value and the lower bound.
        """
        # Set parameters for the solver.
        self._model.Params.LogToConsole = 1

        # Solve the model the first time
        self._model.optimize()

        # Perform multiple iterations.  In each iteration, check if
        # the graph is disconnected, add constraints and omtimize again.
        while not nx.is_connected(self._edge_vars.as_graph()):
            solution = self._edge_vars.as_graph()
            for component in nx.connected_components(solution):
                # we have a disconnected component, add a constraint to connect it
                self._model.addConstr(
                    sum(x for _, x in self._edge_vars.outgoing_edges(component)) >= 2
                )
            # reoptimize, with the added Constraints.
            self._model.optimize()

        assert self._model.Status == gp.GRB.OPTIMAL
