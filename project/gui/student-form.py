import streamlit as st
import pandas as pd
import numpy as np

conn = st.connection("projects", type="sql", url="sqlite:///projects.db")


if 'projects' not in st.session_state:
    st.session_state.projects = pd.read_sql("SELECT name FROM projects", conn.session.bind)
if 'languages' not in st.session_state:
    st.session_state.languages = pd.read_sql("SELECT name FROM programming_languages", conn.session.bind)
projects = st.session_state.projects
languages = st.session_state.languages


st.title("SEP Projekt Anmeldeformular")

with st.form(key="student_form"):
    c1, c2 = st.columns(2)

    first_ame = c1.text_input(
        label="Vorname"
    )
    last_name = c2.text_input(
        label="Name"
    )
    c1, c2 = st.columns(2)
    matrikelnummer = c1.number_input(
        label="Matrikelnummer"
    )


    selected = st.multiselect(
        "projects",
        options=projects['name']
    )
    negatives = st.multiselect(
        "negatives",
        options=projects['name']
    )
    skill = st.radio(
        "skill",
        ["Programmieren", "Schreiben"],
        index=None,
    )
    programing_skills = st.multiselect(
        "Programier skills",
        options=languages['name']
    )

    update_button = st.form_submit_button(label="Anmelden!")

    if update_button:
        if not first_ame or not last_name or not selected or not negatives or not skill or not programing_skills:
            st.warning("Bitte fülle alle felder aus.")
        else:
            pass
            # TODO: Removing old entry from DB, if it exists
            # TODO: Creating new data entry
            new_user_data = {
                        "Vorname": first_ame,
                        "Name": last_name,
                        "Matrikelnummer": matrikelnummer,
                        "projects": selected,
                        "negatives": negatives,
                        "skill": skill,
                        "ProgramierSkills": programing_skills,
                    }
            # TODO: Adding data to the DB
