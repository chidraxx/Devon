

from typing import List


def split_instances(instances: List[str], workers: int):
    instance_groups: List[List[str]] = []
    for i in range(0, len(instances), len(instances) // workers + 1):
        print(i)
        instance_groups.append(instances[max(i-1, 0):i + workers])
    return instance_groups

if __name__ == "__main__":
    instances = [
        "pytest-dev__pytest-5227",
        "sympy__sympy-20212",
        "sympy__sympy-24152",
        "matplotlib__matplotlib-23964",
        "django__django-14855",
    ]
    print(split_instances(instances, 2))

    assert split_instances(instances, 2) == [
        ["pytest-dev__pytest-5227", "sympy__sympy-20212"],
        ["sympy__sympy-24152", "matplotlib__matplotlib-23964", "django__django-14855"],
    ]