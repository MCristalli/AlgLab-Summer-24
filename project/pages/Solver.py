"""
This Code is adapted from the cpsat-primer examples (https://github.com/d-krupke/cpsat-primer) 
by Dominik Krupke, TU Braunschweig, used under CC BY 4.0 
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
import sys
import io
from solver_process import SEPSolverProcess
from solver import SolutionStatCalculator
from data_schema import Instance
from utils import gui_output_to_instance, solution_to_df

# Custom CSS for Text components
st.write("""
    <style>
    [data-testid=stText] {
        border-radius: 0.5em;
        padding: 1rem;
        background: rgb(26, 28, 36);
    }
    </style>
    """, unsafe_allow_html=True)

# Load data if not available
if any(var not in st.session_state for var in ['projects', 'students', 'languages']):
    st.switch_page("Configurator.py")

st.title("SEP Solver")

st.subheader("Configuration")
with st.form("Config", border=False):
    test_config_option = st.number_input("Test Config option", min_value=0, value=100)

    c1, c2 = st.columns([0.75, 0.25])
    solve_button = c1.form_submit_button("Solve", type="primary", use_container_width=True)
    abort_button = c2.form_submit_button("Abort!", type="secondary", use_container_width=True)

# View solution (Filterable Dataframe?)
st.subheader("Solution:")
if "solution" not in st.session_state:
    st.session_state.solution = pd.DataFrame()
solution_placeholder = st.empty()
solution_placeholder.dataframe(st.session_state.solution, hide_index=True, use_container_width=True)

# Solver output and progress bar
progress_spinner = st.empty()

status_placeholder = st.empty()

log_placeholder = st.empty()
if "log_text" not in st.session_state:
    st.session_state.log_text = ""
log_placeholder.text(st.session_state.log_text)


if solve_button:
    with progress_spinner, st.spinner("Calculating Solution..."):
        # Get the instance
        projects = st.session_state.projects
        students = st.session_state.students
        languages = st.session_state.languages
        instance = gui_output_to_instance(projects, students, languages)

        solver_process = SEPSolverProcess(instance)
        solver_process.start()

        st.session_state.log_text = ""
        counter = 0

        while True:
            logs = solver_process.get_log()
            if logs:
                st.session_state.log_text += "".join(logs) + "\n"
            # st.session_state.log_text += logger.get_value()
            log_placeholder.text(st.session_state.log_text)

            if not solver_process.is_running() or abort_button:
                if abort_button:
                    solver_process.interrupt()
                    status_placeholder.warning("Solving process interrupted.")
                else:
                    solution = solver_process.get_solution()
                    if solution is None:
                        status_placeholder.error("No Solution found!")
                        st.stop()
                    solution_stats = SolutionStatCalculator(instance, solution).getStats()
                    st.session_state.log_text += solution_stats
                    log_placeholder.text(st.session_state.log_text)

                    st.session_state.solution = solution_to_df(solution, projects, students)
                    solution_placeholder.dataframe(st.session_state.solution, hide_index=True, use_container_width=True)
                    status_placeholder.success("Solver finished.")
                break
            time.sleep(0.1)