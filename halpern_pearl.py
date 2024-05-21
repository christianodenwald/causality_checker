"""For Halpern & Pearl (2005)"""

from itertools import combinations

VR = {'ML1': {0,1},
      'ML2': {0,1},
      'FB': {0,1}}

# settings
ML1 = 1
ML2 = 1
FB = 1

# F
FB = ML1 and ML2


def wildfire():
    pass


# generate partitions
def generate_partitions(variables):
    partitions = []
    for r in range(1, len(variables)):
        for p in combinations(variables, r):
            partition = [sorted(list(p)), sorted(list(set(variables) - set(p)))]
            partitions.append(partition)
    return partitions


variables = VR.keys()
partitions = generate_partitions(variables)
print(partitions)

#####


class signature:
    pass

class model:
    pass



def test_AC(M, u, cause, effect):
    is_cause = False
    
    print(f'{cause} is {"" if is_cause else "not "} a cause of {effect}.')
    return is_cause