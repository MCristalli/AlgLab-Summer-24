"""
This Code is adapted from the cpsat-primer examples (https://github.com/d-krupke/cpsat-primer) 
by Dominik Krupke, TU Braunschweig, used under CC BY 4.0 
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
from solver_process import SEPSolverProcess
from data_schema import Instance

def calculate_progress(lower_bound, upper_bound):
    """
    Calculate progress as a percentage based on lower and upper bounds.

    Args:
        lower_bound (float): The current lower bound of the solution.
        upper_bound (float): The current upper bound of the solution.

    Returns:
        float: Progress percentage.
    """
    if lower_bound == float("-inf") or upper_bound == float("inf"):
        return 0.0
    return max(0.0, min(1.0, (lower_bound / upper_bound) if upper_bound != 0 else 0.0))


# Custom CSS for Text components
st.write("""
    <style>
    [data-testid=stText] {
        border-radius: 0.5em;
        padding: 1rem;
	    background: rgb(26, 28, 36);
    }
    </style>
    """,unsafe_allow_html=True)

st.title("SEP Solver")

st.subheader("Configuration")
with st.form("Config", border=False):
    test_config_option = st.number_input("Test Congfig option", min_value=0, value=100)

    c1, c2 = st.columns([0.75, 0.25])
    solve_button = c1.form_submit_button("Solve", type="primary", use_container_width=True)
    abort_button = c2.form_submit_button("Abort!", type="secondary", use_container_width=True)

# View solution (Filterable Dataframe?)
st.subheader("Solution:")
if "solution" not in st.session_state:
    st.session_state.solution = pd.DataFrame()
solution_placeholder = st.empty()
solution_placeholder.dataframe(st.session_state.solution, use_container_width=True)

# Solver output and progress bar
lb_ub_placeholder = st.empty()
if "lb_ub" not in st.session_state:
    st.session_state.lb_ub = ""
lb_ub_placeholder.markdown(st.session_state.lb_ub)

progress_bar = st.progress(0)
status_placeholder = st.empty()

log_placeholder = st.empty()
if "log_text" not in st.session_state:
    st.session_state.log_text = ""
log_placeholder.text(st.session_state.log_text)


if solve_button:
    # TODO: get the instance
    with open("./instances/anonymized_data_1.json") as f:
        instance = Instance.model_validate_json(f.read())

    # TODO: get the config options eg:
    # config = {
    #     "test": test_config_option,
    # }

    solver_process = SEPSolverProcess(instance)
    solver_process.start()

    st.session_state.log_text = ""
    counter = 0
    while True:
        lower_bound = solver_process.get_current_bound()
        upper_bound = solver_process.get_current_objective_value()
        st.session_state.lb_ub = (
            f"**Lower bound: {lower_bound}, Upper bound: {upper_bound}**"
        )
        lb_ub_placeholder.markdown(st.session_state.lb_ub)

        logs = solver_process.get_log()
        logs = None
        if logs:
            st.session_state.log_text += "".join(logs) + "\n"
        log_placeholder.text(st.session_state.log_text)

        progress = calculate_progress(lower_bound, upper_bound)
        progress_bar.progress(progress)

        if not solver_process.is_running() or abort_button:
            if abort_button:
                solver_process.interrupt()
                status_placeholder.warning("Solution process interrupted.")
            else:
                st.session_state.solution = pd.DataFrame(solver_process.get_solution())
                print(st.session_state.solution)
                solution_placeholder.dataframe(st.session_state.solution, use_container_width=True)
                status_placeholder.success("Solver finished.")
            break
        time.sleep(0.1)
