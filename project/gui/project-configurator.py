import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
import ast
from typing import List
from typing import Optional
from sqlalchemy import Column, ForeignKey, Table, String, update, select, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Query, declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()

class ProgrammingLanguage(Base):
    __tablename__ = "programming_languages"
    name: Mapped[str] = mapped_column(primary_key=True)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    name: Mapped[str]
    minimum: Mapped[int]
    optimum: Mapped[int]
    maximum: Mapped[int]
    ratio: Mapped[int]
    language_requirements: Mapped[str]

conn = st.connection("projects", type="sql", url="sqlite:///projects.db")
Base.metadata.create_all(conn.engine)

@st.cache_data
def query_projects(_conn):
    projects = pd.read_sql_table("projects", conn.engine, index_col='id')
    # convert str to list
    projects['language_requirements'] = projects['language_requirements'].apply(lambda val: ast.literal_eval(val) if val is not None else list())
    return projects

@st.cache_data
def query_languages(_conn):
    languages = list()
    with _conn.session as session:
        for language in session.query(ProgrammingLanguage):
            languages += [language.name]
    return languages

if 'projects' not in st.session_state:
    st.session_state.projects = query_projects(conn)
if 'languages' not in st.session_state:
    st.session_state.languages = query_languages(conn)
if 'csvbutton' not in st.session_state:
    st.session_state.csvbutton = False


st.title("Project Configurator v3")
selected = option_menu(None, ["Projects", "Programming Languages"], 
    default_index=0, orientation="horizontal")

if selected == "Projects":
    def toggle_csvbutton():
        st.session_state.csvbutton = not st.session_state.csvbutton

    @st.cache_data
    def convert_df(projects):
        # IMPORTANT: Cache the conversion to prevent computation on every rerun
        return projects.to_csv().encode("utf-8")
    csv = convert_df(st.session_state.projects)

    def remove_project(row):
        st.session_state.projects.drop([row], inplace=True)
    def set_project(row, column, key):
        st.session_state.projects.at[row, column] = st.session_state[key]
    def add_project():
        new_project = pd.DataFrame([{
            "name": "Example Project",
            "minimum": 4,
            "optimum": 7,
            "maximum": 10,
            "ratio": 50,
            "language_requirements": [],
        }])
        # Adding new data to the dataframe
        st.session_state.projects = pd.concat(
            [st.session_state.projects, new_project], ignore_index=True
        )

    def add_row(key: int, name: str, minimum: int, optimum: int, maximum: int, ratio: int, language_requirements: List[str]):
        if key is None:
            return
        str_id = str(key)
        # filter out invalid Languages
        language_requirements = [language for language in language_requirements if language in st.session_state.languages]
        with st.expander(name, expanded=True):
            st.text_input("Project Name", name, max_chars=255, key=str_id+"name", on_change=set_project, kwargs=dict(row=key, column="name", key=str_id+"name"))
            c1, c2, c3 = st.columns(3)
            c1.number_input("Minimum", 0, int(optimum), int(minimum), on_change=set_project, kwargs=dict(row=key, column="minimum", key=str_id+"min"), key=str_id+"min")
            c2.number_input("Optimum", int(minimum), int(maximum), int(optimum), on_change=set_project, kwargs=dict(row=key, column="optimum", key=str_id+"opt"), key=str_id+"opt")
            c3.number_input("Maximum", int(optimum), 1000, int(maximum), on_change=set_project, kwargs=dict(row=key, column="maximum", key=str_id+"max"), key=str_id+"max")
            st.slider("Programmer-Writer ratio", 0, 100, ratio, format="%d%%", help="Prozentualer anteil an Programmierern", on_change=set_project, kwargs=dict(row=key, column="ratio", key=str_id+"ratio"), key=str_id+"ratio")
            st.multiselect("Required Skills", st.session_state.languages, default=language_requirements, on_change=set_project, kwargs=dict(row=key, column="language_requirements", key=str_id+"skills"), key=str_id+"skills")
            c0, c1 = st.columns([12, 1]) # TODO: properly align to the right
            c1.button('❌', on_click=remove_project, args=[key], use_container_width=True, key=str_id+"remove")


    c1, c2, c3 = st.columns(3)
    c1.button("Import CSV", on_click=toggle_csvbutton, use_container_width=True)
    c2.download_button("Export CSV", data=csv, file_name="projects.csv", mime="text/csv", use_container_width=True)
    c3.button("Testing", type="primary", use_container_width=True)

    if st.session_state.csvbutton:
        uploaded_files = st.file_uploader("Import CSV", label_visibility="hidden", type=["csv"], accept_multiple_files=True)
        if uploaded_files is not None and len(uploaded_files) > 0:
            st.session_state.projects = pd.concat(
                [pd.read_csv(file, index_col=0, converters={"language_requirements": ast.literal_eval}) for file in uploaded_files], ignore_index=True
            )
            st.session_state.csvbutton = False
            st.rerun()

    st.dataframe(st.session_state.projects, use_container_width=True)
    projects = st.session_state.projects
    projects.apply(lambda row: add_row(**dict({column: row[column] for column in projects.columns}, key=row.name)), axis='columns')

    with st.container(border=True):
        st.button("Add New Project!", on_click=add_project)


    # save edited projects to db
    projects = pd.DataFrame(st.session_state.projects)
    # convert list to str
    projects['language_requirements'] = projects['language_requirements'].apply(str)
    projects.to_sql(name='projects', con=conn.engine, if_exists='replace', index_label='id')


if selected == "Programming Languages":
    def remove_language(index):
        del st.session_state.languages[index]
    def set_language(index, key):
        st.session_state.languages[index] = st.session_state[key]
    def add_language(language):
        st.session_state.languages.append(language)

    def add_row(key, programming_language):
        c1, c2 = st.columns([12, 1])
        c1.text_input("Language "+str(key), programming_language, on_change=set_language, kwargs=dict(index=key, key="Language"+str(key)), key="Language"+str(key), label_visibility='collapsed')
        c2.button("❌", on_click=remove_language, kwargs=dict(index=key), key="remove"+str(key), use_container_width=True)
    
    st.write("Programming Languages")
    for id, language in enumerate(st.session_state.languages):
        add_row(id, language)

    st.button("Add", on_click=add_language, kwargs=dict(language=""), use_container_width=True)


    # Update Database
    languages = st.session_state.languages
    with conn.session as session:
        stmt = delete(ProgrammingLanguage)
        session.execute(stmt)
        stmt = insert(ProgrammingLanguage).values([[language] for language in languages]).on_conflict_do_nothing()
        session.execute(stmt)
        session.commit()
