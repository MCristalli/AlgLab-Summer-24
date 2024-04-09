import itertools
import math
from typing import List

from data_schema import Instance, Item, Solution
from ortools.sat.python.cp_model import FEASIBLE, OPTIMAL, CpModel, CpSolver


class MultiKnapsackSolver:
    """
    This class can be used to solve the Multi-Knapsack problem
    (also the standard knapsack problem, if only one capacity is used).

    Attributes:
    - instance (Instance): The multi-knapsack instance
        - items (List[Item]): a list of Item objects representing the items to be packed.
        - capacities (List[int]): a list of integers representing the capacities of the knapsacks.
    - model (CpModel): a CpModel object representing the constraint programming model.
    - solver (CpSolver): a CpSolver object representing the constraint programming solver.
    """

    def __init__(self, instance: Instance):
        """
        Initialize the solver with the given Multi-Knapsack instance.

        Args:
        - instance (Instance): an Instance object representing the Multi-Knapsack instance.
        """
        self.items = instance.items
        self.capacities = instance.capacities
        self.model = CpModel()
        self.solver = CpSolver()
        self.solver.parameters.log_search_progress = True
        
        self.number_knapsacks = list(range(len(self.capacities)))
        self.number_items = list(range(len(self.items)))
        
        self.x = {}
        for k in self.number_knapsacks:
                for i in self.number_items:
                        self.x[k, i] = self.model.NewBoolVar(f"x_{k}_{i}") 
        
        
        for k in self.number_knapsacks:
        	self.model.Add(sum(self.x[k, i] * self.items[i].weight for i in self.number_items) <= self.capacities[k])
        	
        for i in self.number_items:
        	self.model.Add(sum(self.x[k, i] for k in self.number_knapsacks) <= 1)
        
        summe = 0
        for k in self.number_knapsacks:
                for i in self.number_items:
                	summe += self.x[k, i] * self.items[i].value
                	
        self.model.Maximize(summe)



    def solve(self, timelimit: float = math.inf) -> Solution:
        """
        Solve the Multi-Knapsack instance with the given time limit.

        Args:
        - timelimit (float): time limit in seconds for the cp-sat solver.

        Returns:
        - Solution: a list of lists of Item objects representing the items packed in each knapsack
        """
        # handle given time limit
        if timelimit <= 0.0:
            return Solution(knapsacks=[])  # empty solution
        elif timelimit < math.inf:
            self.solver.parameters.max_time_in_seconds = timelimit
            
        status = self.solver.Solve(self.model)
        
        self.knapsacks = [[] for k in self.number_knapsacks]
        
        for k in self.number_knapsacks:
                for i in self.number_items:
        	        if self.solver.Value(self.x[k, i]) == 1:
        		        self.knapsacks[k].append(self.items[i])
        		        
        return Solution(knapsacks=self.knapsacks)
