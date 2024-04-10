from data_schema import Instance, Solution
from ortools.sat.python import cp_model


def solve(instance: Instance) -> Solution:
    """
    Implement your solver for the problem here!
    """
    numbers = instance.numbers
    model = cp_model.CpModel()

    # IntVars for the minimum and maximum
    minimum = model.NewIntVar(-100, 100, "minimum")
    maximum = model.NewIntVar(-100, 100, "maximum")

    # minmum should be smaller than maximum
    model.Add(minimum <= maximum)

    for num in numbers:
        model.Add(minimum <= num) # the minimum is smaller (or equal) to all the other numbers
        model.Add(maximum >= num) # the maximum is larger (or equal) to all the other numbers

    # A boolean variable for each Value. To select if this is the minimum value.
    mins = [model.NewBoolVar(f"min_{i}") for i in range(len(numbers))]

    # A boolean variable for each Value. To select if this is the maximum value.
    maxs = [model.NewBoolVar(f"max_{i}") for i in range(len(numbers))]

    # Only 1 minimum can exist
    model.Add(sum(mins) == 1)
    # Only 1 maximum can exist
    model.Add(sum(maxs) == 1) 

    # maximize the distance between any 2 numbers.
    model.add(minimum == sum(x * i for x, i in zip(mins, numbers)))

    model.Add(maximum ==  sum(x * i for x, i in zip(maxs, numbers)))

    # find the actual largest difference.
    model.Maximize(maximum - minimum)

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    status = solver.Solve(model)

    assert status == cp_model.OPTIMAL

    return Solution(
        number_a=solver.Value(minimum),
        number_b=solver.Value(maximum),
        distance=abs(solver.Value(minimum) - solver.Value(maximum)),
    )
