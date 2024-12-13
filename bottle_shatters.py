from collections import OrderedDict
import itertools
import copy


variables = ['ST', 'BT', 'SH', 'BH', 'BS']
initial_values = [1, 1, 1, 0, 1]
exo_variables = ['ST', 'BT']
# endo_variables_id = [variables.index(v) for v in variables if not v in exo_variables]
variables_id = list(range(0, len(variables)))
vranges = [[0, 1], [0, 1], [0, 1], [0, 1], [0, 1]]


####################################
def update(se):
    se[2] = se[0]
    se[3] = int(not se[0] and se[1])
    se[4] = int(se[2] or se[3])
    return se


se = [1, 1, None, None, None]
update(se)

####################################

def update2(se, i):
    if i == 2:
        se[2] = se[0]
    if i == 3:
        se[3] = int(not se[0] and se[1])
    if i == 4:
        se[4] = int(se[2] or se[3])
    return se

se = [1, 1, None, None, None]
for i, v in enumerate(se):
    if not v:
        update2(se, i)

# contingency



####################################



def intervention(se, i, iv):
    se[i] = iv
    return se

se = intervention(se, 2, 0) # Suzy misses


####################################

def all_splits_with_mandatory_element(lst, mandatory_element):
    if mandatory_element not in lst:
        raise ValueError("The mandatory element must be in the list.")

    lst_without_mandatory = [x for x in lst if x != mandatory_element]
    all_splits = []
    n = len(lst_without_mandatory)

    for i in range(n + 1):
        for combo in itertools.combinations(lst_without_mandatory, i):
            list1 = list(combo) + [mandatory_element]
            list2 = [x for x in lst if x not in list1]
            all_splits.append((list1, list2))

    return all_splits

def powerset(iterable):
    s = list(iterable)
    return list(itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1)))

def calculate_phi(se):
    return se[-1]

print()
def check_causality_HP(se, cause, phi):
    all_splits = all_splits_with_mandatory_element(variables_id, 0)
    for partition in all_splits:  # all possible partitions of V in Z and W
        Z, W = partition
        settings = list(itertools.product(*vranges))
        for setting in settings:  # all possible settings
            se_mod = copy.copy(se)
            intervention(se_mod, cause, 0)  # X <- x'
            for w in W:
                intervention(se_mod, w, setting[w])
            if calculate_phi(se_mod) != phi: # if AC2(a) holds
                z_subsets = powerset(Z)
                w_subsets = powerset(W)
                for z_subset in z_subsets:
                    for w_subset in w_subsets:
                        sez = copy.copy(se)
                        intervention(sez, cause, 1)  # X <- x
                        for w in w_subset:
                            intervention(sez, w, setting[w])
                        for z in z_subset:
                            intervention(sez, z, setting[z])
                        # propagate
                        for i, v in enumerate(sez):
                            if not v:
                                update2(sez, i)
                        # check if phi
                        if calculate_phi(sez) != phi:
                            break
                print(f'AC2 satsified.\nZ: {Z}\nW: {W}\nSettings:{setting}')
    #             break
    #     break
    # return True

se = [1, 1, None, None, None]
is_cause = check_causality_HP(se, 0, 1)