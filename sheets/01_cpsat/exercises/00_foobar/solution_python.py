from data_schema import Instance, Solution


def solve(instance: Instance) -> Solution:
    """
    Implement your solver for the problem here!
    """
    numbers = instance.numbers
    maximum = max(numbers)
    minimum = min(numbers)
    return Solution(
        number_a=maximum,
        number_b=minimum,
        distance=abs(maximum - minimum),
    )
