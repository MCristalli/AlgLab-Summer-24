from typing import Any, List
from data_schema import *

import gurobipy as gp
import networkx as nx
from gurobipy import GRB
import math


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
            for p in self._projects
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
        self._languages = [l for l in instance.programming_languages]
        self._model = gp.Model()
        self._model.ModelSense = -1
        self._assignment_vars = _AssignmentVariables(self._students.values(), self._projects.values(), self._model)
        self._abs_diff = self._model.addVars(len(self._projects), vtype=GRB.CONTINUOUS, name="abs_diff")
        self._opt_size_diff = self._model.addVars(len(self._projects), vtype=GRB.CONTINUOUS, name="opt_size_diff")
        self._skill_coverage = self._model.addVars(len(self._projects), len(self._languages), vtype=GRB.BINARY, name="skill_coverage")
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
        print(len(programmers_count))
        for project in self._projects.values():
            programmers_count[project.id] = sum(
                x if self._students[s].skill == 0 else 0 for (s, p), x in self._assignment_vars if p == project.id)
            writers_count[project.id] = sum(
                x if self._students[s].skill == 1 else 0 for (s, p), x in self._assignment_vars if p == project.id)
            self._model.addConstr(
                self._abs_diff[project.id] >= writers_count[project.id] - programmers_count[project.id])
            self._model.addConstr(
                self._abs_diff[project.id] >= programmers_count[project.id] - writers_count[project.id])

        # Constraint for helper variable skill_coverage
        for project in self._projects.values():
            langCount = 0
            for lang in self._languages:
                # Anzahl der Studenten im Projekt p, die Skill k mit mindestens 2 haben
                if project.language_requirements[langCount] == 1:
                    num_students_with_skill = gp.quicksum(
                        x * (self._students[s].programing_skills.get(lang) >= 2) for (s, p), x in self._assignment_vars if p == project.id)
                # Setze skill_coverage[p, k] auf 1, wenn mindestens zwei Studenten Skill k mit mindestens 2 haben
                    self._model.addConstr(self._skill_coverage[project.id, langCount] <= num_students_with_skill)
                if project.language_requirements[langCount] == 0:
                    self._model.addConstr(self._skill_coverage[project.id, langCount] == 0)
                langCount += 1

        # Minimum one student with minimum beginner level for every required skill per project
        for project in self._projects.values():
            langCount = 0
            for lang in self._languages:
                self._model.addConstr(sum(x * self._students[s].programing_skills.get(lang) for (s, p), x in self._assignment_vars if p == project.id) \
                   >= project.language_requirements[langCount])
                langCount += 1

        # Constrain the absolute difference from optimal size
        for project in self._projects.values():
            students_in_project = sum(x for (s, p), x in self._assignment_vars if p == project.id)
            self._model.addConstr(
                self._opt_size_diff[project.id] >= students_in_project - project.opt)
            self._model.addConstr(
                self._opt_size_diff[project.id] >= project.opt - students_in_project)

            #Objective 1: Do not assign students to projects they dislike
        self._model.setObjectiveN(
            sum(x if p not in self._students[s].negatives else 0 for (s, p), x in self._assignment_vars),
            index=0,
            priority=6, weight=2)

            #Objective 2: Assign students to preferred projects. 2 points for assignment to preferred project, 1 for neutral
        self._model.setObjectiveN(
            sum(x if p not in self._students[s].projects else 2 * x for (s, p), x in self._assignment_vars), index=1,
            priority=5, weight=2)

            #Objective 3: Maximize the number of groups which have at least on advanced student for every required skill
        self._model.setObjectiveN(gp.quicksum(self._skill_coverage[p, k] for p in range(len(self.instance.projects)) for k in range(len(self.instance.programming_languages))), \
                                  index=2, priority=4, weight=1)

            #Objective 4: Minimize the difference from the optimal project size
        self._model.setObjectiveN(-sum(self._opt_size_diff[j] for j in range(len(self.instance.projects))), index=3,
                                  priority=3, weight=0.5)

            #Objetive 5: Minimize the difference between number of programmers and number of writers in each group.
            #The absolute difference is subtracted from objective value
        self._model.setObjectiveN(-sum(self._abs_diff[j] for j in range(len(self.instance.projects))), index=4, priority=2,
                                  weight=1)

            #Objective 6: Maximize the number of students assigned to a project where at least on of their skills is required
        self._model.setObjectiveN(sum(x for (s, p), x in self._assignment_vars if any(self._students[s].programing_skills.get(skill) >= 1 for (skill, skillInt) in zip(self.instance.programming_languages,self._projects[p].language_requirements ) if skillInt == 1) ), \
                                  index=5, priority=1, weight=1)
    def solve(self, callbacks = None) -> Solution:
        """
        Calculate the optimal solution to the problem.
        """
        # Set parameters for the solver.
        self._model.Params.LogToConsole = 0

        def callback(model, where):
            # This callback is called by Gurobi on various occasions, and
            # we can react to these occasions.
            if where == gp.GRB.Callback.MESSAGE:
                if callbacks and ('Message' in callbacks):
                    message = model.cbGet(GRB.Callback.MSG_STRING)
                    callbacks['Message'](message)

        self._model.optimize(callback)

        # perform multiple iterations here if necessary

        return Solution(assignments=list(self._assignment_vars.as_dict().items()))

    def count_difference_from_optimal_size(self, solution: Solution) -> List[int]:
        optimal_size = [project.opt for project in self.instance.projects]
        student_count = [0 for _ in range(len(self.instance.projects))]
        for student_id, assigned_project in solution.assignments:
            student_count[assigned_project] += 1

        diff_from_opt_size = [abs(student_count[project] - optimal_size[project]) for project in
                              range(len(self.instance.projects))]
        return diff_from_opt_size

    def count_skillDiff_per_project():
        programmers_count = [0 for j in range(len(instance.projects))]
        writers_count = [0 for j in range(len(instance.projects))]

        for student_id, assigned_project in solution.assignments:
            if student_lookup[student_id].skill == 0:
                programmers_count[assigned_project] += 1

            if student_lookup[student_id].skill == 1:
                writers_count[assigned_project] += 1

        skillDiff = [abs(programmers_count[project] - writers_count[project]) for project in
                     range(len(instance.projects))]
        return skillDiff

class SolutionStatCalculator:
    def __init__(self, instance: Instance, solution: Solution) -> None:
        self.instance = instance
        self.solution = solution
        self.student_lookup = {student.id: student for student in self.instance.students}


    def printStats(self):
        preferred_count = self.count_preferred_assignments()
        disliked_count = self.count_disliked_assignments()
        skillDiff = self.count_skillDiff_per_project()
        size_diff = self.count_difference_from_optimal_size()
        number_of_groups_sufficient_advanced = self.count_groups_min_2_skilled()
        potential_use = self.potential_use()

        print(f"Studenten: {len(self.instance.students)}")
        print(f"Projekte: {len(self.instance.projects)}")
        print(f"Studenten mit einem Wunschprojekt: {preferred_count}")
        print(f"Studenten mit einem neutralen Projekt: {len(self.instance.students) - preferred_count - disliked_count}")
        print(f"Studenten mit einem abgewählten Projekt: {disliked_count}")
        print(f"Projekte mit mindestens einem fortgeschrittenen Studenten für jeden benötigten Skill: {number_of_groups_sufficient_advanced}")
        for diff in range(max(size_diff) + 1):
            print(f"Projekte mit einer Differenz zur opt Größe von {diff} : {size_diff.count(diff)}")
        print(f"Potentialnutzung: {potential_use[0]} von {potential_use[1]}")


    def count_preferred_assignments(self) -> int:
        count = 0
        for student_id, assigned_project in self.solution.assignments:
            student_projects = [student.projects for student in self.instance.students if student.id == student_id][0]
            if assigned_project in student_projects:
                count += 1
        print()
        return count
    def count_disliked_assignments(self) -> int:
        count = 0
        for student_id, assigned_project in self.solution.assignments:
            student_negatives = [student.negatives for student in self.instance.students if student.id == student_id][0]

            if assigned_project in student_negatives:
                count += 1
        print()
        return count

    def count_difference_from_optimal_size(self):
        optimal_size = [0 for p in self.instance.projects]
        for i in range(len(self.instance.projects)):
            optimal_size[i] = self.instance.projects[i].opt
        student_count = [0 for i in range(len(self.instance.projects))]
        for student_id, assigned_project in self.solution.assignments:
            student_count[assigned_project] += 1
        diff_from_opt_size = [abs(student_count[project] - optimal_size[project]) for project in
                     range(len(self.instance.projects))]
        return diff_from_opt_size

    def count_groups_min_2_skilled(self) -> int:
        number_of_groups_sufficient_advanced = 0
        for project in self.instance.projects:
            sufficient_advanced = 1
            students_in_project = []
            for student_id, assigned_project in self.solution.assignments:
                if assigned_project == project.id:
                    students_in_project.append(self.student_lookup[student_id])
            langCount = 0
            for lang in self.instance.programming_languages:
                if project.language_requirements[langCount] == 1: # This project requires this language
                    advancedCountforLang = 0
                    for student in students_in_project:
                        if student.programing_skills[lang] >= 2:
                            advancedCountforLang += 1
                    if advancedCountforLang <= 0:
                        sufficient_advanced = 0
                langCount += 1
            number_of_groups_sufficient_advanced = number_of_groups_sufficient_advanced + sufficient_advanced
        return number_of_groups_sufficient_advanced

    def count_stud_min_1_skilled(self):
        student_count = 0
        for student_id, assigned_project in self.solution.assignments:
            langCount = 0
            for skill_lvl in self.student_lookup[student_id].programing_skills.values():
                if skill_lvl >= 1 and self.instance.projects[assigned_project].language_requirements[langCount] == 1:
                    student_count += 1
                    break
                langCount += 1
        return student_count

    def potential_use(self):
        overall_potential = sum(sum(student.programing_skills.values()) for student in self.instance.students)
        used_potential = 0
        for student_id, assigned_project in self.solution.assignments:
            for lang, langInt in zip(self.instance.programming_languages, range(len(self.instance.programming_languages))):
                if self.instance.projects[assigned_project].language_requirements[langInt]:
                    used_potential = used_potential + self.student_lookup[student_id].programing_skills[lang]
        return used_potential, overall_potential

    def count_skillDiff_per_project(self):
        programmers_count = [0 for j in range(len(self.instance.projects))]
        writers_count = [0 for j in range(len(self.instance.projects))]

        for student_id, assigned_project in self.solution.assignments:
            if self.student_lookup[student_id].skill == 0:
                programmers_count[assigned_project] += 1

            if self.student_lookup[student_id].skill == 1:
                writers_count[assigned_project] += 1

        skillDiff = [abs(programmers_count[project] - writers_count[project]) for project in
                     range(len(self.instance.projects))]
        return skillDiff

if __name__ == "__main__":
    # Read the instance
    with open("./instances/anonymized_data_1.json") as f:
        instance: Instance = Instance.model_validate_json(f.read())
        student_lookup = {student.id: student for student in instance.students}
    # Create the solver
    solver = SEPAssignmentSolver(instance)

    solution = solver.solve(callbacks={'Message': lambda msg: print(msg, end='')})
    # Verify the solution
    assert solution is not None, "The solution must not be 'None'!"
    assert isinstance(solution, Solution), "The solution be of type 'Solution'!"
    assert len(solution.assignments) == len(instance.students), "All Students must be assigned a project!"
    for assignment in solution.assignments:
        student_id = assignment[0]
        student = student_lookup[student_id]
        project_id = assignment[1]
        assert student is not None, f"Invalid Student {student_id} found!"

    #checks if theres at least one student with required langauge skill
    for project in instance.projects:
        students_in_project = []
        for student_id, assigned_project in solution.assignments:
            if assigned_project == project.id:
                students_in_project.append(student_lookup[student_id])
        langCount = 0
        for lang in instance.programming_languages:
            if project.language_requirements[langCount] == 1:  # This project requires this language
                # Check if there is at least one student in the project with this language skill
                if not any(student.programing_skills[lang] >= 1 for student in students_in_project):
                    raise AssertionError(
                        f"Project {project.id} does not have a student with the required skill for language {lang}")
            langCount += 1

    # Dump the solution to a file
    solution_json = solution.model_dump_json(indent=2)
    with open("./solution.json", "w") as f:
        f.write(solution_json)

    sol_stat_calculator = SolutionStatCalculator(instance, solution)
    sol_stat_calculator.printStats()




