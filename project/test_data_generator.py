from data_schema import Instance, Student, Project, Solution
import random
import pandas as pd


class Generator:

    def __init__(self):
        self.projects = []
        self.students = []
        self.instance = None
        self.instance_json = None
        self.programing_languages = ["C ", "C++", "C#", "Java", "HTML/CSS", "Python", "JavaScript", "PHP"]
        self.project_min_students = 7
        self.projects_max_students = 13

    def generate_test_data(self, number_students, number_courses, number_positive, number_negative, projects_min_students, projects_max_students) -> Instance:
        self.project_min_students = projects_min_students
        self.projects_max_students = projects_max_students

        self.generate_projects(number_courses)
        self.generate_students(number_students, number_positive, number_negative)

        self.instance = Instance(students=self.students, projects=self.projects, programming_languages=self.programing_languages)
        self.instance_json = self.instance.model_dump_json(indent=2)
        return self.instance

    def save_instance(self, name):
        with open(name, "w") as f:
            f.write(self.instance_json)

    def generate_projects(self, number_courses):
        for i in range(number_courses):
            minimum = random.randint(self.project_min_students, self.projects_max_students)
            maximum = random.randint(minimum, self.projects_max_students)
            optimum = random.randint(minimum, maximum)

            number_programming_languages = random.randint(1, 4)

            required_languages = []
            for v in range(number_programming_languages):
                required_languages.append(random.choice([x for x in self.programing_languages if x not in required_languages]))

            project = Project(id=i, min=minimum, max=maximum, opt=optimum, language_requirements=self.language_requirements_to_int_list(required_languages))
            self.projects.append(project)

    def generate_single_project(self, project_id) -> Project:
        minimum = random.randint(self.project_min_students, self.project_min_students + 2)
        maximum = random.randint(minimum, self.projects_max_students)
        optimum = random.randint(minimum, maximum)

        number_programming_languages = random.randint(1, 4)

        required_languages = []
        for v in range(number_programming_languages):
            required_languages.append(
                random.choice([x for x in self.programing_languages if x not in required_languages]))

        return Project(id=project_id, min=minimum, max=maximum, opt=optimum, language_requirements=self.language_requirements_to_int_list(required_languages))

    def language_requirements_to_int_list(self, list) -> []:
        language_requirements = [0 for x in self.programing_languages]

        for language in list:
            for i in range(len(self.programing_languages)):
                if language == self.programing_languages[i]:
                    language_requirements[i] = 1;

        return language_requirements

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

    def generate_anonymous_data(self, name, number_negative):
        # parse students
        self.parse_anonymous_data(df=pd.read_csv(name))

        # create projects
        project_ids = []

        for student in self.students:
            project_ids = project_ids + student.projects

        project_ids = list(set(project_ids))

        for project_id in project_ids:
            self.projects.append(self.generate_single_project(project_id))

        for student in self.students:
            negatives = []
            for v in range(number_negative):
                choice = random.choice([x.id for x in self.projects if x.id not in student.projects and x.id not in negatives])
                negatives.append(choice)

            student.negatives = negatives;

        self.instance = Instance(students=self.students, projects=self.projects, programming_languages=self.programing_languages)
        self.instance_json = self.instance.model_dump_json(indent=2)

    def parse_anonymous_data(self, df):
        for line in range(len(df["MatrikelNr"])):
            projects = []

            projects.append(int(df["Erstwunsch"][line][8:]) - 1)
            projects.append(int(df["Zweitwunsch"][line][8:]) - 1)
            projects.append(int(df["Drittwunsch"][line][8:]) - 1)

            programing_skills = self.parse_programming_skills(df["Kenntnisse"][line])

            skill = random.randint(0, 1)

            self.students.append(Student(id=df["MatrikelNr"][line], projects=projects, negatives=[], skill=skill,
                                         programing_skills=programing_skills))

    def parse_programming_skills(self, string) -> dict:
        programing_skills = {}
        for language in self.programing_languages:
            if string.find(language) == -1:
                programing_skills[language] = 0
                continue
            substring = string[string.find(language) + len(language):]
            level = substring[substring.find('(') + 1:substring.find(')')]

            if level == "Anfänger":
                programing_skills[language] = 1
            elif level == "Fortgeschritten":
                programing_skills[language] = 2
            elif level == "Experte":
                programing_skills[language] = 3

        return programing_skills

    # converts gui csvs into instance
    def parse_gui_data(self, project_file_name, student_file_name):
        self.parse_gui_projects(project_file_name)
        self.parse_gui_students(student_file_name)

        self.instance = Instance(students=self.students, projects=self.projects,
                                 programming_languages=self.programing_languages)
        self.instance_json = self.instance.model_dump_json(indent=2)
        self.save_instance("./instances/gui_data.json")

    # converts project csv into project instances
    def parse_gui_projects(self, name):
        df = pd.read_csv(name)

        for line in range(len(df["id"])):
            minimum = int(df["minimum"][line])
            maximum = int(df["maximum"][line])
            optimum = int(df["optimum"][line])
            languages = []

            string = str(df["language_required"][line])
            string.replace("'", "")
            languages = string.split(", ")
            l = []

            for language in languages:
                for i in range(len(self.programing_languages)):
                    if language == self.programing_languages[i]:
                        l[i] = 1
                    else:
                        l[i] = 0

            p = Project(id=int(df["id"][line]), min=minimum, max=maximum, opt=optimum, language_requirements=l)

            self.projects.append(p)

    # converts student csv into student variables
    def parse_gui_students(self, name):
        pass

    def anonymized_data_to_gui_readable(self, name):
        self.generate_anonymous_data(name, 3)

        data = []

        for project in self.projects:
            languages = []
            counter = 0
            for i in project.language_requirements:
                if i:
                    languages.append(self.programing_languages[counter])
                counter = counter + 1

            project_data = [
                project.id,
                "Projekt_" + str(project.id + 1),
                project.min,
                project.opt,
                project.max,
                50,
                languages
            ]

            data.append(project_data)

        df = pd.DataFrame(data, columns=["id", "name", "minimum", "optimum", "maximum", "ratio", "language_requirements"])
        df.to_csv("./instances/gui_readable.csv", sep=',', encoding='utf-8', index=False)

    def instance_to_csv(self, original_data_file_name):
        with open("./solution.json") as f:
            solution: Solution = Solution.model_validate_json(f.read())

        data_df = pd.read_csv(original_data_file_name)

        project_ids = []
        for (s_id, p_id) in solution.assignments:
            project_ids.append(p_id)

        project_ids = list(dict.fromkeys(project_ids)) # remove duplicates
        project_ids.sort()

        for p_id in project_ids:
            data = []

            for assignment in solution.assignments:
                if assignment[1] == p_id:
                    name = self.get_name_from_student_id(data_df, assignment[0])
                    data.append([assignment[0], name[0], name[1]])

            df = pd.DataFrame(data, columns=["MatrikelNr", "Nachname", "Vorname"])
            df.to_csv("./assignments/Projekt_" + str(p_id + 1) + ".csv", sep=',', encoding='utf-8', index=False)

    def get_name_from_student_id(self, df, mnr):
        for line in range(len(df["MatrikelNr"])):
            if df["MatrikelNr"][line] == mnr:
                return [df["Nachname"][line], df["Vorname"][line]]



generator = Generator()
#generator.anonymized_data_to_gui_readable("./instances/sep_registrations_1.csv")
generator.instance_to_csv("./instances/sep_registrations_1.csv")
