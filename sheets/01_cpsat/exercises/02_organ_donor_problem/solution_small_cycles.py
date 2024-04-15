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
        self.donations = {(src.id, dst.id): (donor, dst, self.model.NewBoolVar(f"e_{src.id}_{dst.id}")) for src in recipients for donor in self.database.get_partner_donors(src) for dst in self.database.get_compatible_recipients(donor) }

        # No self loops allowed (optional: the problem alredy states, that a recipiants donor are all incompatible)
        for (i, j), (_, _, donoation) in self.donations.items():
            if i == j:
                self.model.Add(donoation == 0)
        
        # at most 1 donation for each recpiants partner donors
        for src in recipients:
            self.model.Add(sum([donoation for (i, j), (_, _, donoation) in self.donations.items() if i == src.id]) <= 1)

        # at most 1 donation for each recpiant (optional: covered by the constraint below)
        for src in recipients:
            self.model.Add(sum([donoation for (i, j), (_, _, donoation) in self.donations.items() if j == src.id]) <= 1)

        # if a recpiant recives a donation the partner donors have to donate.
        # the recieved amount of donations must equal the outgoing ammount of donations.
        for recipient in recipients:
            self.model.Add(sum([donoation for (i, j), (_, _, donoation) in self.donations.items() if j == recipient.id]) == sum([donoation for (i, j), (_, _, donoation) in self.donations.items() if i == recipient.id]))


        # cycles - c_{c}_{r} describes, if the recipient r is on cycles c.
        self.cycles = {r.id: [self.model.NewBoolVar(f"c_{r}_{c}") for c in range(max_cycles)] for r in recipients}

        # a recipient can lie on at most one cycle (optional: covered by the condition below)
        for recipient in recipients:
            self.model.Add(sum(self.cycles[recipient.id]) <= 1)

        # A recipient must lie on a cycle, if someone donates to him
        for recipient in recipients:
            self.model.Add(sum([donoation for (i, j), (_, _, donoation) in self.donations.items() if j == recipient.id]) == sum(self.cycles[recipient.id]))

        # recipients are on the same cycle, if there is a donation between those 2
        for recipient1 in recipients:
            for recipient2 in recipients:
                donation = self.donations.get((recipient1.id, recipient2.id))
                if donation is not None:
                    for c1, c2 in zip(self.cycles[recipient1.id], self.cycles[recipient2.id]):
                        self.model.Add(c1 == c2).OnlyEnforceIf(donation[2])

        # each cycle can contain at most 3 donations
        for cycle in range(max_cycles):
            self.model.Add(sum([self.cycles[recipient.id][cycle] for recipient in recipients]) <= 3)


        # Maximize the length of the cycle aka the ammount of donations
        self.model.Maximize(sum(donoation for (_, _, donoation) in self.donations.values()))


    def optimize(self, timelimit: float = math.inf) -> Solution:
        if timelimit <= 0.0:
            return Solution(donations=[])
        if timelimit < math.inf:
            self.solver.parameters.max_time_in_seconds = timelimit

        status = self.solver.Solve(self.model)
        assert status == OPTIMAL

        return Solution(donations=[Donation(donor=donor, recipient=recipient) for (donor, recipient, donation) in self.donations.values() if self.solver.Value(donation) ])

