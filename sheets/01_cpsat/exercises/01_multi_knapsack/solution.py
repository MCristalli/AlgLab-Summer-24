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
        
        # Variable for each knapsack for each item, that should land in that knapsack
        self.x = [[self.model.NewBoolVar(f"x_{i}{k}") for k in range(len(self.capacities))] for i in range(len(self.items))]

        # Each items can only be in at most 1 knapsack
        for knapsacks in self.x:
            self.model.Add(sum(knapsacks) <= 1)
            
        # capacity constraint for each knapsack
        for k, capacity in enumerate(self.capacities):
           self.model.Add(sum(x[k] * i.weight for x, i in zip(self.x, self.items)) <= capacity)

        # Maximize the value of all the knapsacks
        self.model.Maximize(sum(x * i.value for x_k, i in zip(self.x, self.items) for x in x_k ))



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
        assert status == OPTIMAL
        return Solution(knapsacks=[[i for x, i in zip(self.x, self.items) if self.solver.Value(x[k])] for k in range(len(self.capacities))])
