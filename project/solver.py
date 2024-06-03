from typing import Any, List
from data_schema import *

import gurobipy as gp
import networkx as nx
from gurobipy import GRB

class _AssignmentVariables:
    """
    A helper class that manages the variables for edges in a graph.
    """
    EPSILON = 0.5

    def __init__(self, students: List[Student], projects: List[Project], model: gp.Model):
        self._students = students
        self._projects = projects
        self._model = model
        self._vars = {
            (s.id, p.id): model.addVar(vtype=GRB.BINARY, name=f"assign_{s.id}_{p.id}") 
            for s in self._students
            for p in self._projects if p not in s.negatives
        }

    def x(self, s: Student, p: Project) -> gp.Var:
        """
        Return variable for student project assigment s-> p if available.
        """
        assert p in self._projects
        if p.id in s.projects:
            return self._vars[s.id, p.id]
        else:
            return None

    def __iter__(self):
        """
        Iterate over all edges&variables.
        """
        return iter(self._vars.items())

    def as_dict(self, in_callback: bool = False):
        """
        Return the current solution in a dict.
        """
        if in_callback:
            # If we are in a callback, we need to use the solution from the callback.
            return {s: p for (s, p), x in self if self._model.cbGetSolution(x) > self.EPSILON}
        else:
            # Otherwise, we can use the solution from the model.
            return {s: p for (s, p), x in self if x.X > self.EPSILON}


class SEPAssignmentSolver:
    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self._students = {s.id: s for s in instance.students}
        self._projects = {p.id: p for p in instance.projects}
        self._model = gp.Model()
        self._assignment_vars = _AssignmentVariables(self._students.values(), self._projects.values(), self._model)
        self.setup_constraints()

    def setup_constraints(self) -> None:
        # Project Constraints
        for project in self._projects.values():
            self._model.addConstr(project.max >= sum(x for (s, p), x in self._assignment_vars if p == project.id))
            self._model.addConstr(project.min <= sum(x for (s, p), x in self._assignment_vars if p == project.id))

        # Student Constraints
        for student in self._students.values():
            self._model.addConstr(1 >= sum(x for (s, p), x in self._assignment_vars if s == student.id))

        self._model.setObjective(sum(x if p not in self._students[s].projects else 2 * x for (s, p), x in self._assignment_vars), GRB.MAXIMIZE)



    def solve(self) -> Solution:
        """
        Calculate the optimal solution to the problem.
        """
        # Set parameters for the solver.
        self._model.Params.LogToConsole = 1

        self._model.optimize()

        # perform multiple iterations here if necessary

        return Solution(assignments=list(self._assignment_vars.as_dict().items()))





if __name__ == "__main__":
    # Read the instance
    with open("./instances/100_students_random.json") as f:
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
      # assert project_id in student.projects, f"Student {student_id} got assigned a Project he didnt sign up for!"
    # Dump the solution to a file
    solution_json = solution.model_dump_json(indent=2)
    with open("./solution.json", "w") as f:
        f.write(solution_json)
    # TODO: Do some analysis on the Solution.

    # Count the number of students who were assigned to one of their preferred projects
    def count_preferred_assignments():
        count = 0
        for student_id, assigned_project in solution.assignments:
            student_projects = [student.projects for student in instance.students if student.id == student_id][0]

            if assigned_project in student_projects:
                count += 1
        print()
        return count

    preferred_count = count_preferred_assignments()
    print(f"Anzahl der Studenten mit einem Wunschprojekt: {preferred_count}")
    print(f"Anzahl der Studenten mit einem neutralem Projekt: {len(instance.students) - preferred_count}")