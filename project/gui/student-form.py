import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import insert, delete, select, text
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base


Base = declarative_base()
class Student(Base):
    __tablename__ = 'students'
    matrikelnummer = Column(Integer, primary_key=True)
    firstname = Column(String, nullable=False)
    name = Column(String, nullable=False)
    projects = Column(String, nullable=False)
    negatives = Column(String)
    skill = Column(String, nullable=False)
    programing_skills = Column(String, nullable=False)
    
conn = st.connection("projects", type="sql", url="sqlite:///projects.db")
Base.metadata.create_all(conn.engine)


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
        label="Matrikelnummer",
        value=0,
        format="%i"
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
        if not first_ame or not last_name or not selected or not skill or not programing_skills:
            st.warning("Bitte fülle alle felder aus.")
        else:
            pass
            # Creating new data entry
            new_user_data = {
                        "firstname": first_ame,
                        "name": last_name,
                        "matrikelnummer": matrikelnummer,
                        "projects": str(selected),
                        "negatives": str(negatives),
                        "skill": skill,
                        "programing_skills": str(programing_skills),
                    }
            # Adding data to the DB
            with conn.session as session:
                #  Removing old entry from DB, if it exists
                stmt = delete(Student).where(Student.matrikelnummer == matrikelnummer)
                session.execute(stmt)
                stmt = insert(Student).values(new_user_data)
                session.execute(stmt)
                session.commit()
            st.success("Erfolgreich angemeldet!")