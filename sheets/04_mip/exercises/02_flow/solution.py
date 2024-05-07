import gurobipy as gb
import networkx as nx
from data_schema import Instance, Solution
from gurobipy import GRB
from collections import defaultdict
import math


class MiningRoutingSolver:
    def __init__(self, instance: Instance) -> None:
        self.map = instance.map
        self.budget = instance.budget
        self.model = gb.Model()

        self.tunnel_selection = defaultdict(dict)
        self.real_throughput = defaultdict(dict)
        for tunnel in self.map.tunnels:
            #tunnel selection [from][to]
            self.tunnel_selection[tunnel.location_a][tunnel.location_b] = self.model.addVar(vtype=gb.GRB.BINARY, name=f"edge_in_{tunnel.location_a}_{tunnel.location_b}")
            self.tunnel_selection[tunnel.location_b][tunnel.location_a] = self.model.addVar(vtype=gb.GRB.BINARY, name=f"edge_out_{tunnel.location_b}_{tunnel.location_a}")

            self.real_throughput[tunnel.location_a][tunnel.location_b] = self.model.addVar(vtype=gb.GRB.INTEGER, name=f"real_throughput_{tunnel.location_a}_{tunnel.location_b}")

    def create_solution(self) -> Solution:
        sol = []

        if self.model.Status == GRB.OPTIMAL:
            for tunnel in self.map.tunnels:
                if self.tunnel_selection[tunnel.location_a][tunnel.location_b].X == 1 and self.real_throughput[tunnel.location_a][tunnel.location_b].X > 0:
                    sol.append(((tunnel.location_a, tunnel.location_b), round(self.real_throughput[tunnel.location_a][tunnel.location_b].X)))
                elif self.tunnel_selection[tunnel.location_b][tunnel.location_a].X == 1 and self.real_throughput[tunnel.location_a][tunnel.location_b].X > 0:
                    sol.append(((tunnel.location_b, tunnel.location_a), round(self.real_throughput[tunnel.location_a][tunnel.location_b].X)))

        return Solution(flow=sol)
    def solve(self) -> Solution:
        """
        Calculate the optimal solution to the problem.
        Returns the "flow" as a list of tuples, each tuple with two entries:
            - The *directed* edge tuple. Both entries in the edge should be ints, representing the ids of locations.
            - The throughput/utilization of the edge, in goods per hour
        """

        #Constraints
        # real_throughput <= throughput
        self.model.addConstrs(self.real_throughput[tunnel.location_a][tunnel.location_b] <= tunnel.throughput_per_hour for tunnel in self.map.tunnels)

        # for every mine: sum(real_thoughput[outgoing]) <= sum(real_throughput[incoming]) + om
        for mine in self.map.mines:
            output = 0
            ingoing = 0
            for tunnel in self.map.tunnels:
                if tunnel.location_a == mine.id:
                    output += self.real_throughput[tunnel.location_a][tunnel.location_b] * self.tunnel_selection[tunnel.location_a][tunnel.location_b]
                    ingoing += self.real_throughput[tunnel.location_a][tunnel.location_b] * self.tunnel_selection[tunnel.location_b][tunnel.location_a]
                elif tunnel.location_b == mine.id:
                    output += self.real_throughput[tunnel.location_a][tunnel.location_b] * \
                              self.tunnel_selection[tunnel.location_b][tunnel.location_a]
                    ingoing += self.real_throughput[tunnel.location_a][tunnel.location_b] * \
                             self.tunnel_selection[tunnel.location_a][tunnel.location_b]

            self.model.addConstr(output <= ingoing + mine.ore_per_hour)

        # tunnel is not outgoing and incoming at the same time
        for tunnel in self.map.tunnels:
            self.model.addConstr(self.tunnel_selection[tunnel.location_a][tunnel.location_b] + self.tunnel_selection[tunnel.location_b][tunnel.location_a] <= 1)


        # sum(tunnel_selected * tunnel_cost) <= budget
        self.model.addConstr(sum(self.tunnel_selection[tunnel.location_a][tunnel.location_b] * tunnel.reinforcement_costs + self.tunnel_selection[tunnel.location_b][tunnel.location_a] * tunnel.reinforcement_costs for tunnel in self.map.tunnels) <= self.budget)


        # maximize: sum(real_throughput[incoming elevator] )
        ore_arriving_at_elevator = 0
        for tunnel in self.map.tunnels:
            if tunnel.location_b == self.map.elevator.id:
                ore_arriving_at_elevator += self.real_throughput[tunnel.location_a][tunnel.location_b] * self.tunnel_selection[tunnel.location_a][tunnel.location_b]
            elif tunnel.location_a == self.map.elevator.id:
                ore_arriving_at_elevator += self.real_throughput[tunnel.location_a][tunnel.location_b] * self.tunnel_selection[tunnel.location_b][tunnel.location_a]
        self.model.addConstr(ore_arriving_at_elevator >= 1)

        # no elevator tunnel is outgoing
        self.model.addConstr(sum(self.tunnel_selection[tunnel.location_a][tunnel.location_b] for tunnel in self.map.tunnels if tunnel.location_a == self.map.elevator.id) == 0)

        self.model.setObjective(ore_arriving_at_elevator, GRB.MAXIMIZE)

        self.model.optimize()

        return self.create_solution()
