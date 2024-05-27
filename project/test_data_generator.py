from data_schema import Instance, Student, Project
import random


class Generator:

    def __init__(self):
        self.projects = []
        self.students = []

    def generate_test_data(self, number_students, number_courses, number_positive, number_negative) -> Instance:
        self.generate_projects(number_courses)
        self.generate_students(number_students, number_positive)

        return Instance(students=self.students, projects=self.projects)

    def generate_projects(self, number_courses):
        for i in range(number_courses):
            minimum = random.randint(3, 7)
            project = Project(id=i, min=minimum, max=minimum + 4)
            self.projects.append(project)

    def generate_students(self, number_students, number_positive):
        for i in range(number_students):
            projects = []
            for v in range(number_positive):
                choice = random.choice([x for x in self.projects if x not in projects])
                projects.append(choice.id)

            self.students.append(Student(id=i, projects=projects))

