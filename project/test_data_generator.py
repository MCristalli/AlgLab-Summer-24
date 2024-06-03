from data_schema import Instance, Student, Project
import random


class Generator:

    def __init__(self):
        self.projects = []
        self.students = []

    def generate_test_data(self, number_students, number_courses, number_positive, number_negative) -> Instance:
        self.generate_projects(number_courses)
        self.generate_students(number_students, number_positive, number_negative)

        self.instance = Instance(students=self.students, projects=self.projects)
        self.instance_json = self.instance.model_dump_json(indent=2)
        return self.instance

    def save_instance(self, name):
        with open(name, "w") as f:
            f.write(self.instance_json)

    def generate_projects(self, number_courses):
        for i in range(number_courses):
            minimum = random.randint(5, 8)
            project = Project(id=i, min=minimum, max=minimum + 4)
            self.projects.append(project)

    def generate_students(self, number_students, number_positive, number_negative):
        for i in range(number_students):
            projects = []
            negatives = []
            for v in range(number_positive):
                choice = random.choice([x.id for x in self.projects if x.id not in projects and x.id not in negatives])
                projects.append(choice)

            for v in range(number_negative):
                choice = random.choice([x for x in self.projects if x not in projects and x not in negatives])
                negatives.append(choice.id)

            skill = random.randint(0, 1)

            self.students.append(Student(id=i, projects=projects, negatives=negatives, skill=skill))


generator = Generator()
generator.generate_test_data(100, 15, 3, 3)
generator.save_instance("./instances/100_students_random.json")
