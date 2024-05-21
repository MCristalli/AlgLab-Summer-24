from typing import Any, List
from data_schema import *

import gurobipy as gp
import networkx as nx
from gurobipy import GRB

class _EdgeVariables:
    """
    A helper class that manages the variables for edges in a graph.
    """
    EPSILON = 0.5

    def __init__(self, G: nx.Graph, model: gp.Model):
        self._graph = G
        self._model = model
        self._vars = {
            (u, v): model.addVar(vtype=GRB.BINARY, name=f"edge_{u}_{v}") 
            for u, v in self._graph.edges
        }

    def x(self, u, v) -> gp.Var:
        """
        Return variable for edge (u, v).
        """
        if (u, v) in self._vars:
            return self._vars[u, v]
        # If (u,v) was not found, try (v,u)
        return self._vars[v, u]

    def outgoing_edges(self, vertices):
        """
        Return all edges&variables that are outgoing from the given vertices.
        """
        # Not super efficient, but efficient enough for our purposes.
        for (u, v), x in self._vars.items():
            if u in vertices and v not in vertices:
                yield (u, v), x
            elif v in vertices and u not in vertices:
                yield (v, u), x

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
            used_edges = [uv for uv, x in self if self._model.cbGetSolution(x) > self.EPSILON]
        else:
            # Otherwise, we can use the solution from the model.
            used_edges = [uv for uv, x in self if x.X > self.EPSILON]
        return nx.Graph(used_edges)


class SEPAssignmentSolver:
    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self._model = gp.Model()
        self._graph = nx.Graph([(student.id, -project_id) for student in self.instance.students for project_id in student.projects]) # graph from student to project
        self._assignment_vars = _EdgeVariables(self._graph, self._model)
        self.setup_constraints()

    def setup_constraints(self) -> None:
        #setup initial constraints and the objective here.
        pass


    def solve(self) -> Solution:
        """
        Calculate the optimal solution to the problem.
        """
        # Set parameters for the solver.
        self._model.Params.LogToConsole = 1

        self._model.optimize()

        # perform multiple iterations here if necessary

        return Solution(assignments=[])





if __name__ == "__main__":
    # Read the instance
    with open("./instances/instance_1.json") as f:
        instance: Instance = Instance.model_validate_json(f.read())
        student_lookup = {student.id: student for student in instance.students}
    # Create the solver
    solver = SEPAssignmentSolver(instance)
    solution = solver.solve()
    # Verify the solution
    assert solution is not None, "The solution must not be 'None'!"
    assert isinstance(solution, Solution), "The solution be of type 'Solution'!"
    assert len(solution.assignments) == len(instance.students), "All Students must be assigned a project!"
    for assignment in solution.assignments:
        student_id = assignment[0]
        student = student_lookup[student_id]
        project_id = assignment[1]
        assert student is not None, f"Invalid Student {student_id} found!"
        assert project_id in student.projects, f"Student {student_id} got assigned a Project he didnt sign up for!"
    # Dump the solution to a file
    solution_json = solution.model_dump_json(indent=2)
    with open("./solution.json", "w") as f:
        f.write(solution_json)
    # TODO: Do some analysis on the Solution.
