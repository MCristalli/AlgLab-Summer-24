from data_schema import Instance, Student, Project, Solution
import random
import pandas as pd
import ast


def get_name_from_student_id(df, mnr):
    return [df.at[mnr, "name"], df.at[mnr, "firstname"]]


def get_name_from_project_id(df, p_id):
    return df.at[p_id, "name"]



def gui_output_to_instance(df_projects, df_students, languages) -> Instance:

    projects = []

    students = []

    # turn df_projects into Projects
    for p_id, row in df_projects.iterrows():
        project_languages = row["language_requirements"]
        #print(lan)
        language_req = [0 for x in languages]

        counter = 0
        for language in languages:

            for l in project_languages:

                if language == l:
                    language_req[counter] = 1
            counter = counter + 1


        projects.append(Project(id=p_id, min=row["minimum"], max=row["maximum"], opt=row["optimum"], language_requirements=language_req))

    for matrikelnummer, row in df_students.iterrows():
        s_projects = row["projects"]

        s_projects = [df_projects.index[df_projects['name'] == negative][0] for negative in row["projects"]]

        s_negatives = [df_projects.index[df_projects['name'] == negative][0] for negative in row["negatives"]]

        skill = row["skill"] == "Schreiben"

        programing_skills = {}
        for language in languages:
            level = row["programing_skills"].get(language, None)
            if level == "Anfänger":
                programing_skills[language] = 1
            elif level == "Fortgeschritten":
                programing_skills[language] = 2
            elif level == "Experte":
                programing_skills[language] = 3
            else:
                programing_skills[language] = 0

        students.append(Student(id=matrikelnummer, projects=s_projects, negatives=s_negatives, skill=skill, programing_skills=programing_skills))

    return Instance(students=students, projects=projects, programming_languages=languages)



def solution_to_df(solution, projects_df, students_df) -> pd.DataFrame:
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
        merged_df = pd.concat([merged_df, df], ignore_index=True)
        df.to_csv("./assignments/" + str(get_name_from_project_id(projects_df, p_id)) + ".csv", sep=',', encoding='utf-8', index=False)

    return merged_df
