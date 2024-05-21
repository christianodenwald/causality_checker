"Loader example"

from itertools import combinations, product
from typing import List

A = 1
B = 0
C = 1
D = (A and B) or C

structural_equations = {
    'A': lambda v: v['A'],
    'B': lambda v: v['B'],
    'C': lambda v: v['C'],
    'D': lambda v: (v['A'] and v['B']) or v['C']
}

# variables = ['A', 'B', 'C', 'D']
vvalues = {'A': 1, 'B': 0, 'C': 1, 'D': 1}
vrange = {X:[0,1] for X in vvalues.keys()}
vformulas = {}

# calculate values from model:
values = {variable: equation(vvalues) for variable, equation in structural_equations.items()}

class CausalModel:
    def __init__(self, vvalues, vrange, equations):
        self.vvalues = vvalues
        self.vrange = vrange
        self.equations = equations

loader = CausalModel(vvalues, vrange, structural_equations)

def generate_partitions(variables, causes):
    partitions = {}
    xvariables = [a for a in variables if a not in causes] # X must be in Z
    for r in range(len(variables) + 1 - len(causes)):  # Include possibility of empty set
        for p in combinations(xvariables, r):
            partition = {'Z': sorted(list(p) + causes), 'W': sorted(list(set(xvariables) - set(p)))}
            partitions[len(partitions)] = partition
    return partitions

def generate_combinations(input_dict):
    keys = input_dict.keys()
    value_combinations = product(*(input_dict[key] for key in keys))
    result = [dict(zip(keys, combination)) for combination in value_combinations]
    return result

def is_cause(model:CausalModel, context, phi, X:dict, theory):
    variables = model.vvalues.keys()

    # sanity checks
    assert set(X.keys()) <= set(variables), 'X must be among the model variables'

    # generate all possible partitions of Z and W
    partitions = generate_partitions(variables, list(X.keys()))

    # check all possible settings (x', w') of (X, W)
    for partition in partitions.values():


        # get values Z=z*
        zstar = {a:vvalues[a] for a in partition['Z']}

        xwdict = {a:vrange[a] for a in list(X.keys()) + partition['W'] }
        for xwvalues in generate_combinations(xwdict):
            print(xwvalues)



X = {'A': 1}
partitions = generate_partitions(list(vvalues.keys()), list(X.keys()))
partition = partitions[1]

is_cause(loader, vvalues, {'D': 1}, {'A': 1}, 'HPo')

print()