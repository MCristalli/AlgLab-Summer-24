from data_schema import Instance, Student, Project
import random
import pandas as pd


class Generator:

    def __init__(self):
        self.projects = []
        self.students = []
        self.instance = None
        self.instance_json = None

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
                choice = random.choice([x.id for x in self.projects if x.id not in projects and x.id not in negatives])
                negatives.append(choice)

            skill = random.randint(0, 1)

            self.students.append(Student(id=i, projects=projects, negatives=negatives, skill=skill))

    def generate_anonymous_data(self, name):
        # parse students
        self.parse_anonymous_data(df=pd.read_csv(name))

        # create projects
        project_ids = []

        for student in self.students:
            project_ids = project_ids + student.projects

        project_ids = list(set(project_ids))
        minimum = random.randint(5, 8)

        for id in project_ids:
            self.projects.append(Project(id=id, min=minimum, max=minimum+4))

        self.instance = Instance(students=self.students, projects=self.projects)
        self.instance_json = self.instance.model_dump_json(indent=2)

    def parse_anonymous_data(self, df):
        for line in range(len(df["MatrikelNr"])):
            projects = []

            projects.append(int(df["Erstwunsch"][line][8:]))
            projects.append(int(df["Zweitwunsch"][line][8:]))
            projects.append(int(df["Drittwunsch"][line][8:]))

            skill = random.randint(0, 1)

            self.students.append(Student(id=df["MatrikelNr"][line], projects=projects, negatives=[], skill=skill))


#generator = Generator()
#generator.generate_anonymous_data("./instances/sep_registrations_1.csv")
#generator.save_instance("./instances/anonymized_data_1")
#generator.generate_anonymous_data("./instances/sep_registrations_2.csv")
#generator.save_instance("./instances/anonymized_data_2")

