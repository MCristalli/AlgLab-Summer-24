import math
from collections import defaultdict

import networkx as nx
from data_schema import Donation, Solution
from database import TransplantDatabase
from ortools.sat.python.cp_model import FEASIBLE, OPTIMAL, CpModel, CpSolver


class CycleLimitingCrossoverTransplantSolver:
    def __init__(self, database: TransplantDatabase) -> None:
        """
        Constructs a new solver instance, using the instance data from the given database instance.
        :param Database database: The organ donor/recipients database.
        """

        self.database = database
        recipients = self.database.get_all_recipients()
        max_cycles = len(recipients) // 2 # each cycles needs at least 2 nodes

        self.model = CpModel()
        self.solver = CpSolver()
        self.solver.parameters.log_search_progress = True

        # donations - (Donor, Recipient, e_{i, j})
        #   e_{i, j}     - if the donor is making a donation for recipiant i to recipiant j
        #                  aka if the edge (i, j) is on the cycle
        self.donations = {(src.id, dst.id): (donor, dst) for src in recipients for donor in self.database.get_partner_donors(src) for dst in self.database.get_compatible_recipients(donor) }

        # Pre process for cycle constraints.
        # G = the Graph induced by the donations.
        G = nx.DiGraph(self.donations.keys())

        # cycles - the cycle and a boolean variable for each cyle Graph G denoted by the donations.
        #          equals 1 if cycle c_i is slected.
        #          Also the cycle
        self.cycles = [(cycle, self.model.NewBoolVar(f"c_{i}")) for i, cycle in enumerate(nx.simple_cycles(G, 3))]

        # A recipient can only occour in at most one cycle
        for recipient in recipients:
            self.model.Add(sum([cycle_var for cycle, cycle_var in self.cycles if recipient.id in cycle]) <= 1)

        # Maximize the length of the cycle aka the ammount of donations
        self.model.Maximize(sum(len(cycle) * cycle_var for cycle, cycle_var in self.cycles))


    def optimize(self, timelimit: float = math.inf) -> Solution:
        if timelimit <= 0.0:
            return Solution(donations=[])
        if timelimit < math.inf:
            self.solver.parameters.max_time_in_seconds = timelimit

        status = self.solver.Solve(self.model)
        assert status == OPTIMAL

        return Solution(donations=[Donation(donor=self.donations.get((src, dst))[0], recipient=self.donations.get((src, dst))[1]) for cycle, cycle_var in self.cycles if self.solver.Value(cycle_var) for (src, dst) in zip(cycle, cycle[1:] + cycle[:1])  ] )

