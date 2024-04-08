from data_schema import Instance, Solution
from ortools.sat.python import cp_model


def solve(instance: Instance) -> Solution:
    """
    Implement your solver for the problem here!
    """
    numbers = instance.numbers
    model = cp_model.CpModel()
    
    first = [model.NewBoolVar(f"first_{i}") for i in range(len(numbers))]
    second = [model.NewBoolVar(f"second_{i}") for i in range(len(numbers))]
    
    model.Add(sum(f * 1 for f in first) == 1)
    model.Add(sum(s * 1 for s in second) == 1)
    
    
    model.Maximize(sum(f * number for f, number in zip(first, numbers)) - sum(s * number for s, number in zip(second, numbers)))
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    assert( status == cp_model.OPTIMAL)
    
    return Solution(
        number_a = sum(solver.Value(f) * number for f, number in zip(first, numbers)),
        number_b = sum(solver.Value(s) * number for s, number in zip(second, numbers)),
        distance=sum(solver.Value(f) * number for f, number in zip(first, numbers)) - sum(solver.Value(s) * number for s, number in zip(second, numbers)),
    )
