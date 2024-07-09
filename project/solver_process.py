"""
This Code is adapted from the cpsat-primer examples (https://github.com/d-krupke/cpsat-primer) 
by Dominik Krupke, TU Braunschweig, used under CC BY 4.0 
"""
import multiprocessing
import signal
import os
from typing import Dict, Optional, Callable
from data_schema import Solution, Instance
from solver import SEPAssignmentSolver


def _entry_point_solver_process(
    instance, config_options, max_time, lower_bound, upper_bound, log_conn, solution_conn
):
    """
    Entry point for the optimization process. Runs the SEPSolver on the given instance and
    communicates progress and solutions to the main process through pipes.
    """

    # Signal handler for SIGINT signal, no operation needed.
    # This is to prevent the solver from crashing when interrupted, as we are using
    # SIGINT to tell gurobi to stop the search.
    def signal_handler(sig, frame):
        pass

    signal.signal(signal.SIGINT, signal_handler)

    # Initialize the solver
    # solver = SEPAssignmentSolver(instance, config_options)
    solver = SEPAssignmentSolver(instance)

    # Define callback to update the shared lower bound value
    def update_lower_bound(value):
        lower_bound.value = value

    # Define callback to update the shared upper bound value
    def update_upper_bound(value):
        lower_bound.value = value

    # Set solver callbacks
    callbacks = {
        # send log messages through the log pipe
        "Message": lambda msg: log_conn.send([msg]),
        # send solutions through the solution pipe
        # "SolutionCallback": lambda solution: solution_conn.send(solution.model_dump())
    }

    try:
        # Solve the problem with the specified maximum time and callback
        solution = solver.solve(callbacks=callbacks)

        # If a solution is found, send the final solution through the solution pipe
        if solution is not None:
            solution_conn.send(solution.model_dump())
    finally:
        # Close the communication pipes
        log_conn.close()
        solution_conn.close()


class SEPSolverProcess:
    """
    Wrapper for the SEPAssignmentSolver class that runs it in a separate process.
    Provides methods to start, interrupt, and retrieve the solution in a non-blocking manner.
    """

    def __init__(self, instance: Instance, config_options = None, max_time: float = 600.0):
        self.instance = instance
        self.config_options = config_options
        self.max_time = max_time
        self._shared_bound_value = multiprocessing.Value("d", float("-inf"))
        self._shared_objective_value = multiprocessing.Value("d", float("inf"))
        self._log_pipe = multiprocessing.Pipe(duplex=True)
        self._solution_pipe = multiprocessing.Pipe(duplex=True)
        self.process = multiprocessing.Process(
            target=_entry_point_solver_process,
            args=(
                self.instance,
                self.config_options,
                self.max_time,
                self._shared_bound_value,
                self._shared_objective_value,
                self._log_pipe[1],
                self._solution_pipe[1],
            ),
        )
        self._solution = None

    def start(self):
        """Starts the optimization process."""
        self.process.start()

    def interrupt(self):
        """Interrupts the optimization process."""
        if self.process.pid and self.process.is_alive():
            os.kill(self.process.pid, signal.SIGINT)

    def is_running(self):
        """Returns True if the optimization process is still running."""
        return self.process.is_alive()

    def get_solution(self) -> Optional[Solution]:
        """Returns the latest solution found by the solver, or None if no solution is found."""
        solution_data = None
        while self._solution_pipe[0].poll():
            solution_data = self._solution_pipe[0].recv()
        if solution_data is not None:
            self._solution = Solution(**solution_data)
        return self._solution

    def get_current_objective_value(self):
        """Returns the current objective value."""
        return self._shared_objective_value.value

    def get_current_bound(self):
        """Returns the current lower bound."""
        return self._shared_bound_value.value

    def get_log(self) -> list[str]:
        """Returns the latest log entries from the solver."""
        logs = []
        while self._log_pipe[0].poll():
            logs.extend(self._log_pipe[0].recv())
        return logs

    def __del__(self):
        """Cleans up the process when the object is deleted."""
        if self.process.is_alive():
            self.interrupt()
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.terminate()
            self.process.close()
