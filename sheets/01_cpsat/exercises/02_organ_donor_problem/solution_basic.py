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
        
        self.model = CpModel()
        
        self.all_donors = self.database.get_all_donors()
        self.all_recipients = self.database.get_all_recipients()
        
        self.compatible_recipients = {}
        for donor in self.all_donors:
        	self.compatible_recipients[donor] = self.database.get_compatible_recipients(donor)
        	
        self.compatible_donors = {}
        for recipient in self.all_recipients:
                self.compatible_donors[recipient] = self.database.get_compatible_donors(recipient)
        
        
        self.donates = {}
        for donor in self.all_donors:
                for recipient in self.compatible_recipients[donor]:
                        self.donates[donor.id, recipient.id] = self.model.NewBoolVar(f"donates_{donor.id}_{recipient.id}")
                        
                        
        for donor in self.all_donors:
        	# maximum of 1 donation per donor
                self.model.Add(sum(self.donates[donor.id, recipient.id] for recipient in self.compatible_recipients[donor]) <= 1)
                
                
                # donor cannot donate to incompatible recipient
                #self.model.Add(sum(self.donates[donor.id, recipient.id] for recipient in [item for item in self.database.get_all_recipients() if item not in self.database.get_compatible_recipients(donor)]) == 0)
                
        for recipient in self.all_recipients:
        	# every recipient receives a maximum of 1 organ
                self.model.Add(sum(self.donates[donor.id, recipient.id] for donor in self.compatible_donors[recipient]) <= 1)
                
                # recipients can't get an organ from incompatible donor
                #self.model.Add(sum(self.donates[donor.id, recipient.id] for donor in [item for item in self.database.get_all_donors() if item not in self.database.get_compatible_donors(recipient)]) == 0)
                
                #self.model.Add(sum(self.donates[donor.id, recipient.id] for donor in self.database.get_partner_donors(recipient)) <=1)
                
                # organs received - organs donated for a recipient schould be 0
                number_received = sum(self.donates[donor.id, recipient.id] for donor in self.compatible_donors[recipient])
                number_donated = 0
                
                for donor in self.database.get_partner_donors(recipient):
                        for rec in self.compatible_recipients[donor]:
                                number_donated += self.donates[donor.id, rec.id]
                self.model.Add(number_received - number_donated == 0)
                
        #for donor, recipient in zip(self.database.get_all_donors(), self.database.get_all_recipients()):
        	#self.model.Add(self.donates[donor.id, recipient.id] == self.receives[recipient.id, donor.id])
                
        # maximize number of donations
        summe = 0
        for donor in self.all_donors:
                for recipient in self.compatible_recipients[donor]:
                        summe += self.donates[donor.id, recipient.id]
        self.model.Maximize(summe)       
        

        self.solver = CpSolver()
        self.solver.parameters.log_search_progress = True


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
        
        self.status = self.solver.Solve(self.model)
        
        assert (self.status == OPTIMAL)
        
        donations = []
        donator = 0
        recipient = 0
        for don in self.all_donors:
                for rec in self.compatible_recipients[don]:
                        if self.solver.Value(self.donates[don.id, rec.id]) == 1:
                                donation = Donation(donor=don, recipient=rec)
                                donations.append(donation)
                                print(donation)
                                

        return Solution(donations=donations)
