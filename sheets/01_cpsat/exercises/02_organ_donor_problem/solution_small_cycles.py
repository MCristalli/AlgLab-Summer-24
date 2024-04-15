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
        max_cycles = len(recipients)

        self.model = CpModel()
        self.solver = CpSolver()
        self.solver.parameters.log_search_progress = True

        # donations - (Donor, Recipient, e_{i, j}, [c_{c}_{i, j}])
        #   e_{i, j}     - if the donor is making a donation for recipiant i to recipiant j
        #                  aka if the edge (i, j) is on the cycle
        #   c_{c}_{i, j} - describes, if the donation i->j is on cycles c.
        self.donations = {(src.id, dst.id): (donor, dst, self.model.NewBoolVar(f"e_{src.id}_{dst.id}"), [self.model.NewBoolVar(f"c_{c}_{src.id}-{dst.id}") for c in range(max_cycles)]) for src in recipients for donor in self.database.get_partner_donors(src) for dst in self.database.get_compatible_recipients(donor) }

        # No self loops allowed (optional: the problem alredy states, that a recipiants donor are all incompatible)
        for (i, j), (_, _, donoation, _) in self.donations.items():
            if i == j:
                self.model.Add(donoation == 0)
        
        # only at most 1 donation for each recpiants partner donors
        for src in recipients:
            self.model.Add(sum([donoation for (i, j), (_, _, donoation, _) in self.donations.items() if i == src.id]) <= 1)

        # if a recpiant recives a donation the partner donors have to donate.
        # the recieved amount of donations must equal the outgoing ammount of donations.
        for recipient in recipients:
            self.model.Add(sum([donoation for (i, j), (_, _, donoation, _) in self.donations.items() if j == recipient.id]) == sum([donoation for (i, j), (_, _, donoation, _) in self.donations.items() if i == recipient.id]))


        # each edge corresponds to a donation
        for (donor, dst, donation, cycles) in self.donations.values():
            self.model.Add(sum(cycles) == donation)
            # a donation can lie on at most one cycle (optional: included in the above constraint)
            self.model.Add(sum(cycles) <= 1)

        # a donation is on the same cycle if it is on the same path
        for recipient in recipients:
            donations_in  = [cycles for (i, j), (_, _, donoation, cycles) in self.donations.items() if j == recipient.id]
            donations_out = [cycles for (i, j), (_, _, donoation, cycles) in self.donations.items() if i == recipient.id]

            for cycle in range(max_cycles):
                self.model.Add(sum([donations_in_cycles[cycle] for donations_in_cycles in donations_in]) == sum([donations_out_cyces[cycle] for donations_out_cyces in donations_out]))


        # each cycle can contain at most 3 donations
        for cycle in range(max_cycles):
            self.model.Add(sum(cycles[cycle] for (_, _, _, cycles) in self.donations.values()) <= 3)


        # Maximize the length of the cycle aka the ammount of donations
        self.model.Maximize(sum(donoation for (_, _, donoation, _) in self.donations.values()))


    def optimize(self, timelimit: float = math.inf) -> Solution:
        if timelimit <= 0.0:
            return Solution(donations=[])
        if timelimit < math.inf:
            self.solver.parameters.max_time_in_seconds = timelimit

        status = self.solver.Solve(self.model)
        assert status == OPTIMAL

        return Solution(donations=[Donation(donor=donor, recipient=recipient) for (donor, recipient, donation, _) in self.donations.values() if self.solver.Value(donation) ])

