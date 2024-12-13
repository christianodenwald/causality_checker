import copy, itertools
### VIGNETTE 1

ff_disj = {'variables':['ML', 'L', 'FF'],
              'initial_values':[1, 1, 1],
              'current_values':[0, 1, 1],
              'value_ranges': [{0,1}, {0,1}, {0,1},],
              'structural_equations':[None, None, None]}
# ff_disj['current_values'] = ff_disj['initial_values']
ff_disj['structural_equations'][2] = lambda: ff_disj['current_values'][0] or ff_disj['current_values'][1]

### VIGNETTE 2

ff_conj = copy.deepcopy(ff_disj)
ff_conj['structural_equations'][2] = lambda: ff_conj['current_values'][0] and ff_conj['current_values'][1]


### VIGNETTE 3

bottle_shatters = {'variables':['ST', 'BT', 'SH', 'BH', 'BS'],
              'initial_values':[1, 1, 1, 0, 1],
              'current_values':[None]*5,
              'value_ranges': [{0,1}]*5,
              'structural_equations':[None]*5}

bottle_shatters['structural_equations'][2] = lambda: bottle_shatters['current_values'][0]
bottle_shatters['structural_equations'][3] = lambda: bottle_shatters['current_values'][1] or not bottle_shatters['current_values'][2]
bottle_shatters['structural_equations'][4] = lambda: bottle_shatters['current_values'][2] or bottle_shatters['current_values'][3]

###################################


def powerset(iterable):
    s = list(iterable)
    return list(itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1)))
def check_causality_H2015(vignette, cause_variable, cause_value, effect_variable, effect_value):

    # only works for single conjuncts for now, both for cause and effect

    ### preparation
    endo_variable_index = [index for index, item in enumerate(vignette['structural_equations']) if item is not None]
    exo_variable_index = [index for index, item in enumerate(vignette['structural_equations']) if item == None]
    cause_index = vignette['variables'].index(cause_variable)
    effect_index = vignette['variables'].index(effect_variable)


    ### AC1 is implied

    ### AC2am
    x_prime = None
    for x in vignette['value_ranges'][cause_index]:
        if x != effect_value:
            x_prime = x

    for subset_w in powerset(endo_variable_index):
        for i in exo_variable_index:
            vignette['current_values'][i] = vignette['initial_values'][i]
        for i in endo_variable_index:
            vignette['current_values'][i] = None
        # print(subset_w)
        # set X=x' and W=w'
        for i in subset_w:
            vignette['current_values'][i] = vignette['initial_values'][i]
        vignette['current_values'][cause_index] = x_prime
        # propagate with newly set values
        for i in endo_variable_index:
            if i not in subset_w:
                vignette['current_values'][i] = int(vignette['structural_equations'][i]())
        if vignette['current_values'][effect_index] != effect_value:
            return True
    return False





if __name__ == '__main__':
    check_causality_H2015(ff_conj, 'ML', 1, 'FF', 1) # True
    check_causality_H2015(ff_disj, 'ML', 1, 'FF', 1) # False
    check_causality_H2015(bottle_shatters, 'ST', 1, 'BS', 1) # True
    check_causality_H2015(bottle_shatters, 'BT', 1, 'BS', 1) # False


print()