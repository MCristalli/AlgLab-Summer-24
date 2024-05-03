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

    def __init__(self, G: nx.Graph, model: gp.Model):
        self._graph = G
        self._model = model
        self._vars = {
            (u, v): model.addVar(vtype=gp.GRB.BINARY, name=f"edge_{u}_{v}")
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
            used_edges = [vw for vw, x in self if self._model.cbGetSolution(x) > 0.5]
        else:
            # Otherwise, we can use the solution from the model.
            used_edges = [vw for vw, x in self if x.X > 0.5]
        return nx.Graph(used_edges)


class GurobiTspSolver:
    """
    IMPLEMENT ME!
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
        self._edge_vars = _EdgeVariables(G, self._model)



    def get_lower_bound(self) -> float:
        """
        Return the current lower bound.
        """
        # TODO: Implement me!

    def get_solution(self) -> typing.Optional[nx.Graph]:
        """
        Return the current solution as a graph.
        """
        if self._model.status == gp.GRB.OPTIMAL:
            return self._edge_vars.as_graph()

    def get_objective(self) -> typing.Optional[float]:
        """
        Return the objective value of the last solution.
        """
        obj = self._model.getObjective()
        return obj.getValue()

    def first_solve(self):
        for node in self.graph.nodes:
            self._model.addConstr(
                sum(x for _, x in self._edge_vars.incident_edges(node)) == 2
            )

        self._model.setObjective(sum(v * self.graph[u[0]][u[1]]["weight"] for u, v in self._edge_vars), gp.GRB.MINIMIZE)

    def solve(self, time_limit: float, opt_tol: float = 0.001) -> None:
        """
        Solve the model and return the objective value and the lower bound.
        """
        # Set parameters for the solver.
        self._model.Params.LogToConsole = 1
        self._model.Params.TimeLimit = time_limit
        self._model.Params.lazyConstraints = 1
        self._model.Params.MIPGap = (
            opt_tol  # https://www.gurobi.com/documentation/11.0/refman/mipgap.html
        )

        def callback(model, where):
            if where == gp.GRB.Callback.MIPSOL:
                solution = self._edge_vars.as_graph(in_callback=True)
                comps = list(nx.connected_components(solution))
                if len(comps) == 1:
                    return  # solution is connected
                for comp in comps:
                    model.cbLazy(
                        sum(x for _, x in self._edge_vars.outgoing_edges(comp)) >= 2
                    )
        self.first_solve()
        self._model.optimize(callback)

