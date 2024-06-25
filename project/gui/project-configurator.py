import streamlit as st
import pandas as pd
import numpy as np
import ast
from typing import List
from typing import Optional
from sqlalchemy import Column, ForeignKey, Table, String, insert, update, select
from sqlalchemy.orm import Query, declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()

project_language_requirements_association = Table(
    "project_language_requirements",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id")),
    Column("language_requirement_id", ForeignKey("programming_languages.id")),
)

class ProgrammingLanguage(Base):
    __tablename__ = "programming_languages"
    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    name: Mapped[str]

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    name: Mapped[str]
    minimum: Mapped[int]
    optimum: Mapped[int]
    maximum: Mapped[int]
    ratio: Mapped[int]
    language_requirements: Mapped[List[ProgrammingLanguage]] = relationship(ProgrammingLanguage, secondary=project_language_requirements_association, backref='Project')


conn = st.connection("projects", type="sql", url="sqlite:///projects.db")
Base.metadata.create_all(conn.engine)

def insert_into_projects(name, minimum, optimum, maximum, ratio, language_requirements):
    with conn.session as session:
        session.add(Project(name=name, minimum=minimum, optimum=optimum, maximum=maximum, ratio=ratio, language_requirements=[session.get(ProgrammingLanguage, languages[name]) for name in language_requirements]))
        session.commit()

def update_project_by_id(id, name, minimum, optimum, maximum, ratio, language_requirements):
    with conn.session as session:
        project = session.get(Project, id)
        project.name = name
        project.minimum = minimum
        project.optimum = optimum
        project.maximum = maximum
        project.ratio = ratio
        project.language_requirements = [session.get(ProgrammingLanguage, languages[name]) for name in language_requirements]
        session.commit()

projects = []
for (project,) in conn.session.execute(select(Project)):
    projects += [{
        "id": project.id,
        "name": project.name,
        "minimum": project.minimum,
        "optimum": project.optimum,
        "maximum": project.maximum,
        "ratio": project.ratio,
        "language_requirements": [language.name for language in project.language_requirements],
    }]

languages = {}
for (language,) in conn.session.execute(select(ProgrammingLanguage)):
    languages.update({
        language.name: language.id,
    })


if 'csvbutton' not in st.session_state:
    st.session_state.csvbutton = False
def toggle_button():
    st.session_state.csvbutton = not st.session_state.csvbutton

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode("utf-8")
csv = convert_df(pd.DataFrame.from_records(projects, index='id'))

st.title("Project Configurator v2")
c1, c2, c3 = st.columns(3)
c1.button("Import CSV", on_click=toggle_button, use_container_width=True)
c2.download_button("Export CSV", data=csv, file_name="projects.csv", mime="text/csv", use_container_width=True)
c3.button("Testing", type="primary", use_container_width=True)

if st.session_state.csvbutton:
    uploaded_file = st.file_uploader("Import CSV", label_visibility="hidden")
    if uploaded_file is not None:
        dataframe = pd.read_csv(uploaded_file)
        projects = dataframe.to_dict('records')
        for project in projects:
            update_project_by_id(**dict(project, language_requirements=ast.literal_eval(project['language_requirements'])))
        st.session_state.csvbutton = False
        st.rerun()

def add_row(id: int, name: str = "Example Project", minimum: int = 4, optimum: int = 7, maximum: int = 10, ratio: int = 50, language_requirements: List[str] = list()):
    name_out = st.text_input("Project Name", name, max_chars=255, key=str(id)+"pnam")
    c1, c2, c3 = st.columns(3)
    minimum_out = c1.number_input("Minimum", 0, maximum, minimum, key=str(id)+"c1")
    optimum_out = c2.number_input("Optimum", minimum, maximum, optimum, key=str(id)+"c2")
    maximum_out = c3.number_input("Maximum", minimum, 1000, maximum, key=str(id)+"c3")
    ratio_out = st.slider("Programmer-Writer ratio", 0, 100, ratio, format="%d%%", help="Prozentualer anteil an Programmierern", key=str(id)+"pslider")
    language_requirements_out = st.multiselect("Required Skills", languages.keys(), default=language_requirements, key=str(id)+"skills")
    update_project_by_id(id, name_out, minimum_out, optimum_out, maximum_out, ratio_out, language_requirements_out)

for project in projects:
    with st.container(border=True):
        add_row(**project)

with st.container(border=True):
    if st.button("Add New Project!"):
        insert_into_projects("Project Name", 4, 5, 7, 50.0, list())
        st.rerun()
