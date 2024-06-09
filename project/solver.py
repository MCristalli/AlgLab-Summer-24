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
        self._model.ModelSense = -1
        self._assignment_vars = _AssignmentVariables(self._students.values(), self._projects.values(), self._model)
        self._abs_diff = self._model.addVars(len(self._projects), vtype=GRB.CONTINUOUS, name="abs_diff")
        self.setup_constraints()

    def setup_constraints(self) -> None:
        # Project Constraints
        for project in self._projects.values():
            self._model.addConstr(project.max >= sum(x for (s, p), x in self._assignment_vars if p == project.id))
            self._model.addConstr(project.min <= sum(x for (s, p), x in self._assignment_vars if p == project.id))

        # Student Constraints
        for student in self._students.values():
            self._model.addConstr(1 >= sum(x for (s, p), x in self._assignment_vars if s == student.id))

        # abs_diff Constraints
        programmers_count = [0 for p in self._projects.values()]
        writers_count = [0 for p in self._projects.values()]
        for project in self._projects.values():
            programmers_count[project.id] = sum(x if self._students[s].skill == 0 else 0 for (s, p), x in self._assignment_vars if p == project.id)
            writers_count[project.id] = sum(x if self._students[s].skill == 1 else 0 for (s, p), x in self._assignment_vars if p == project.id)
            self._model.addConstr(self._abs_diff[project.id] >= writers_count[project.id] - programmers_count[project.id])
            self._model.addConstr(self._abs_diff[project.id] >= programmers_count[project.id] - writers_count[project.id])

        #Objective 1: Assign students to preferred projects. 2 points for assignment to preferred project, 1 for neutral
        self._model.setObjectiveN(sum(x if p not in self._students[s].projects else 2 * x for (s, p), x in self._assignment_vars), index=0, priority=0, weight=2)

        # Objetive 2: Minimize the difference between number of programmers and number of writers in each group.
        # The absolute difference is subtracted from objective value
        self._model.setObjectiveN(-sum(self._abs_diff[j] for j in range(len(instance.projects))), index=1, priority=0, weight=1)

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

    # Counts the absolute difference between number of programmers and writers for each group
    def count_skillDiff_per_project():
        programmers_count = [0 for j in range(len(instance.projects))]
        writers_count = [0 for j in range(len(instance.projects))]

        for student_id, assigned_project in solution.assignments:
            if student_lookup[student_id].skill == 0:
                programmers_count[assigned_project] += 1

            if student_lookup[student_id].skill == 1:
                writers_count[assigned_project] += 1

        skillDiff = [abs(programmers_count[project] - writers_count[project]) for project in range(len(instance.projects))]
        return skillDiff

    preferred_count = count_preferred_assignments()
    skillDiff = count_skillDiff_per_project()
    print(f"Anzahl der Studenten mit einem Wunschprojekt: {preferred_count}")
    print(f"Anzahl der Studenten mit einem neutralem Projekt: {len(instance.students) - preferred_count}")
    for diff in range(max(skillDiff) + 1):
        print(f"Anzahl der Projekte mit einer Schreiber/Programmierer Differenz von {diff} : {skillDiff.count(diff)}")