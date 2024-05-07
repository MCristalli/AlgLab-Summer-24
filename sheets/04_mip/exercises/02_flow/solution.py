import gurobipy as gb
import networkx as nx
from data_schema import Instance, Solution
from gurobipy import GRB


class _EdgeVariables:
    """
    A helper class that manages the variables for the edges.
    Such a helper class turns out to be useful in many cases.
    """

    def __init__(self, G: nx.Graph, model: gb.Model):
        self._graph = G.to_directed()
        self._model = model
        self._vars = {
            (u, v): model.addVar(vtype=GRB.BINARY, name=f"edge_{u}_{v}") 
            for u, v in self._graph.edges
        }

    def x(self, u, v) -> gb.Var:
        """
        Return variable for edge (u, v), negated if inputs were flipped.
        """
        assert (u, v) in self._vars
        return self._vars[u, v]

    def outgoing_edges(self, vertices):
        """
        Return all edges&variables that are outgoing from the given vertices.
        """
        # Not super efficient, but efficient enough for our purposes.
        for (v, w), x in self._vars.items():
            if v in vertices and w not in vertices:
                yield (v, w), x

    def incident_edges(self, v):
        """
        Return all edges&variables that are incident to the given vertex.
        """
        for n in self._graph.neighbors(v):
            yield (n, v), self.x(n, v)

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


class _FlowVariables:
    """
    A helper class that manages the variables for the edges.
    Such a helper class turns out to be useful in many cases.
    """
    EPSILON = 0.5 # if the weight of an edge exceeds this value it is considered selected.

    def __init__(self, G: nx.Graph, model: gb.Model):
        # Convert to directed Graph for one flow var in each direction
        self._graph = G.to_directed()
        self._model = model
        self._vars = {
            (u, v): model.addVar(vtype=GRB.INTEGER, name=f"flow_{u}_{v}") 
            for u, v in self._graph.edges
        }

    def x(self, u, v) -> gb.Var:
        """
        Return variable for edge (u, v).
        """
        assert (u, v) in self._vars
        return self._vars[u, v]

    def outgoing_edges(self, vertices):
        """
        Return all edges&variables that are outgoing from the given vertices.
        """
        # Not super efficient, but efficient enough for our purposes.
        for (v, w), x in self._vars.items():
            if v in vertices and w not in vertices:
                yield (v, w), x

    def incident_edges(self, v):
        """
        Return all edges&variables that are incident to the given vertex.
        """
        for n in self._graph.neighbors(v):
            yield (n, v), self.x(n, v)

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
            used_edges = [(*vw, {"flow": x.X}) for vw, x in self if self._model.cbGetSolution(x) >= self.EPSILON]
        else:
            # Otherwise, we can use the solution from the model.
            used_edges = [(*vw, {"flow": x.X}) for vw, x in self if x.X >= self.EPSILON]

        return nx.DiGraph(used_edges)


class MiningRoutingSolver:
    def __init__(self, instance: Instance) -> None:
        self.budget = instance.budget # total allowance on all tunnels
        self.map = instance.map
        self.elevator = self.map.elevator
        self.graph = nx.Graph()
        self.graph.add_nodes_from([(mine.id, {"production": mine.ore_per_hour}) for mine in self.map.mines])
        self.graph.add_edges_from([(tunnel.location_a, tunnel.location_b, {"throughput": tunnel.throughput_per_hour, "cost": tunnel.reinforcement_costs}) for tunnel in self.map.tunnels])
        assert self.elevator.id in self.graph.nodes

        self._model = gb.Model()
        # Flow variables for a node
        self._flow_vars = _FlowVariables(self.graph, self._model)
        # if an edge is used at all
        self._edge_vars = _EdgeVariables(self.graph, self._model)


        for (u, v) in self.graph.edges:
            # only one direction per tunnel
            self._model.addConstr(self._edge_vars.x(u, v) + self._edge_vars.x(v, u) <= 1)
            # combined capacity constraint
            self._model.addConstr(self._flow_vars.x(u, v) + self._flow_vars.x(v, u) <= self.graph.edges[u, v]["throughput"])

        # edge capacity constraints 
        for edge, flow_var in self._flow_vars:
            # upper bound for the throughput
            self._model.addConstr(flow_var <= self.graph.edges[edge]["throughput"])

        
        for edge, flow_var in self._flow_vars.outgoing_edges([self.elevator.id]):
            # No outgoing Flow from the elevator
            self._model.addConstr(flow_var == 0)

        # Flow in if we allow flow in that direction - Flow out if we allow flow out in that direction + production >= 0. Flow out of a node should atleast be Flow in plus the production
        for (node, production) in self.graph.nodes(data="production"):
            if node != self.elevator.id:
                self._model.addConstr(sum(flow_var * self._edge_vars.x(u, v) for (u, v), flow_var in self._flow_vars.incident_edges(node))
                                    - sum(flow_var * self._edge_vars.x(u, v) for (u, v), flow_var in self._flow_vars.outgoing_edges([node])) + production >= 0)


        # total budget constraint
        self._model.addConstr(sum(self.graph.edges[edge]["cost"] * edge_var for edge, edge_var in self._edge_vars) <= self.budget)

        # Maximize Flow Objective (the flow comming into the elevators node)
        self._model.setObjective(sum(flow_var * self._edge_vars.x(*edge) for edge, flow_var in self._flow_vars.incident_edges(self.elevator.id)), GRB.MAXIMIZE)





    def solve(self) -> Solution:
        """
        Calculate the optimal solution to the problem.
        Returns the "flow" as a list of tuples, each tuple with two entries:
            - The *directed* edge tuple. Both entries in the edge should be ints, representing the ids of locations.
            - The throughput/utilization of the edge, in goods per hour
        """
        self._model.optimize()
        solution_graph = self._flow_vars.as_graph()
        return Solution(flow=[((u, v), flow) for (u, v, flow) in solution_graph.edges(data="flow")])