from data_schema import Instance, Student, Project, Solution
import random
import pandas as pd
import ast


def get_name_from_student_id(df, mnr):
    for line in range(len(df["matrikelnummer"])):
        if df["matrikelnummer"][line] == mnr:
            return [df["name"][line], df["firstname"][line]]


def get_name_from_project_id(df, p_id):
    for line in range(len(df["id"])):
        if df["id"][line] == p_id:
            return df["name"][line]



def gui_output_to_instance(df_projects, df_students, languages) -> Instance:

    df_students = pd.read_csv("students.csv")
    df_projects = pd.read_csv("projects.csv")

    df_projects.to_csv("./instances/projects.csv", sep=',', encoding='utf-8', index=False)
    df_students.to_csv("./instances/students.csv", sep=',', encoding='utf-8', index=False)


    projects = []

    students = []

    # turn df_projects into Projects
    for p_id in range(len(df_projects["id"])):
        string = str(df_projects["language_requirements"][p_id])
        string = string.replace("[", "").replace("]", "").replace("'", "")

        project_languages = string.split(", ")
        #print(lan)
        language_req = [0 for x in languages]

        counter = 0
        for language in languages:

            for l in project_languages:

                if language == l:
                    language_req[counter] = 1
            counter = counter + 1


        projects.append(Project(id=df_projects["id"][p_id], min=df_projects["minimum"][p_id], max=df_projects["maximum"][p_id], opt=df_projects["optimum"][p_id], language_requirements=language_req))

    for i in range(len(df_students["matrikelnummer"])):
        s_projects = str(df_students["projects"][i]).split(",")

        for name in range(len(s_projects)):
            for x in range(len(df_projects["id"])):
                if s_projects[name] == df_projects["name"][x]:
                    s_projects[name] = df_projects["id"][x]
                    break

        s_negatives = str(df_students["negatives"][i]).split(",")
        for name in range(len(s_negatives)):
            for x in range(len(df_projects["id"])):
                if s_negatives[name] == df_projects["name"][x]:
                    s_negatives[name] = df_projects["id"][x]
                    break

        skill = df_students["skill"][i] == "Schreiben"

        students.append(Student(id=df_students["matrikelnummer"][i], projects=s_projects, negatives=s_negatives, skill=skill, programing_skills=ast.literal_eval(str(df_students["programing_skills"][i]))))

    return Instance(students=students, projects=projects, programming_languages=languages)



def solution_to_df(solution) -> pd.DataFrame:
    projects_df = pd.read_csv("./instances/projects.csv")
    students_df = pd.read_csv("./instances/students.csv")
    merged_df = pd.DataFrame([], columns=["Projekt", "MatrikelNr", "Nachname", "Vorname"])

    project_ids = []
    for (s_id, p_id) in solution.assignments:
        project_ids.append(p_id)

    project_ids = list(dict.fromkeys(project_ids)) # remove duplicates
    project_ids.sort()

    for p_id in project_ids:
        data = []

        for assignment in solution.assignments:
            if assignment[1] == p_id:

                name = get_name_from_student_id(students_df, assignment[0])
                p_name = get_name_from_project_id(projects_df, p_id)
                data.append([p_name, assignment[0], name[0], name[1]])

        df = pd.DataFrame(data, columns=["Projekt", "MatrikelNr", "Nachname", "Vorname"])
        merged_df.append(df)
        df.to_csv("./assignments/" + str(get_name_from_project_id(p_id)) + ".csv", sep=',', encoding='utf-8', index=False)

    return merged_df
