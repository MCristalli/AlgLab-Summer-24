import math

import networkx as nx
from data_schema import Donation, Solution
from database import TransplantDatabase
from ortools.sat.python.cp_model import FEASIBLE, OPTIMAL, CpModel, CpSolver


class CrossoverTransplantSolver:
    def __init__(self, database: TransplantDatabase) -> None:
        """
        Constructs a new solver instance, using the instance data from the given database instance.
        :param Database database: The organ donor/recipients database.
        """
        self.database = database
        recipients = self.database.get_all_recipients()

        self.model = CpModel()
        self.solver = CpSolver()
        self.solver.parameters.log_search_progress = True

        # donors - e_{i, j} if the donor is making a donation for recipiant i to recipiant j
        #          aka if the edge (i, j) is on the cycle
        self.donors = {(src.id, dst.id): (donor, dst, self.model.NewBoolVar(f"e_{src.id}_{dst.id}")) for src in recipients for donor in self.database.get_partner_donors(src) for dst in self.database.get_compatible_recipients(donor) }

        
        # No self loops allowed (optional: the problem alredy states, that a recipiants donor are all incompatible)
        for (i, j), (_, _, donoation) in self.donors.items():
            if i == j:
                self.model.add(donoation == 0)
        
        # only at most 1 donation for each recpiants partner donors
        for src in recipients:
            self.model.add(sum([donoation for (i, j), (_, _, donoation) in self.donors.items() if i == src.id]) <= 1)

        # if a recpiant recives a donation the partner donors have to donate.
        # the recieved amount of donations must equal the outgoing ammount of donations.
        for recipient in recipients:
            self.model.add(sum([donoation for (i, j), (_, _, donoation) in self.donors.items() if j == recipient.id]) == sum([donoation for (i, j), (_, _, donoation) in self.donors.items() if i == recipient.id]))


        # Maximize the length of the cycle aka the ammount of donations
        self.model.maximize(sum(donoation for (_, _, donoation) in self.donors.values()))


    def optimize(self, timelimit: float = math.inf) -> Solution:
        """
        Solves the constraint programming model and returns the optimal solution (if found within time limit).
        :param timelimit: The maximum time limit for the solver.
        :return: A list of Donation objects representing the best solution, or None if no solution was found.
        """
        if timelimit <= 0.0:
            return Solution(donations=[])
        if timelimit < math.inf:
            self.solver.parameters.max_time_in_seconds = timelimit
        
        status = self.solver.Solve(self.model)
        assert status == OPTIMAL

        return Solution(donations=[Donation(donor=donor, recipient=recipient) for (i, j), (donor, recipient, donation) in self.donors.items() if self.solver.Value(donation) ])

