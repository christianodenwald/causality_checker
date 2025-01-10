import copy, itertools

from data import example_data
from data.example_data import *


def generate_vignettes():
    ### VIGNETTE 1

    ff_disj = { 'name': 'FF Disjunctive',
        'variables': ['ML', 'L', 'FF'],
               'initial_values': [1, 1, 1],
               'current_values': [None]*3,
               'value_ranges': [{0, 1}, {0, 1}, {0, 1}, ],
               'structural_equations': [None, None, None]}
    ff_disj['structural_equations'][2] = lambda: ff_disj['current_values'][0] or ff_disj['current_values'][1]

    ### VIGNETTE 2

    ff_conj = copy.deepcopy(ff_disj)
    ff_conj['name'] = 'FF Conjunctive'
    ff_conj['structural_equations'][2] = lambda: ff_conj['current_values'][0] and ff_conj['current_values'][1]

    ### VIGNETTE 3

    bottle_shatters = {'variables': ['ST', 'BT', 'SH', 'BH', 'BS'],
                       'name': 'Bottle Shatters',
                       'initial_values': [1, 1, 1, 0, 1],
                       'current_values': [None] * 5,
                       'value_ranges': [{0, 1}] * 5,
                       'structural_equations': [None] * 5}

    bottle_shatters['structural_equations'][2] = lambda: bottle_shatters['current_values'][0]
    bottle_shatters['structural_equations'][3] = lambda: bottle_shatters['current_values'][1] and not \
        bottle_shatters['current_values'][2]
    bottle_shatters['structural_equations'][4] = lambda: bottle_shatters['current_values'][2] or \
                                                         bottle_shatters['current_values'][3]

    return [ff_disj, ff_conj, bottle_shatters]

def generate_vignettes_from_json(vignettes_json):
    vignettes = []

    for vignette_data in vignettes_json['vignettes']:
        vignette = {
            'vignette_id': vignette_data['id'],
            'name': vignette_data['title'],
            'variables': list(vignette_data['variables'].keys()),
            'initial_values': [0] * len(vignette_data['variables']),
            'current_values': [None] * len(vignette_data['variables']),
            'value_ranges': [set(var['range']) for var in vignette_data['variables'].values()],
            'structural_equations': [None] * len(vignette_data['variables']),
        }

        for var, equation in vignette_data['structural_equations'].items():
            var_index = vignette['variables'].index(var)
            vignette['structural_equations'][var_index] = lambda: eval(equation, {}, {
                key: vignette['current_values'][vignette['variables'].index(key)]
                for key in vignette['variables']
            })

        for var, var_info in vignette_data['variables'].items():
            var_index = vignette['variables'].index(var)
            vignette['initial_values'][var_index] = var_info.get('default', 0)

        vignettes.append(vignette)

    return vignettes


def get_initial_values_from_json(settings_json, vignette_id):
    for setting in settings_json['initial_values']:
        if setting['vignette_id'] == vignette_id:
            return setting['initial_values']
    return None


def get_queries_from_json(queries_json, vignette_id):
    return [query for query in queries_json['queries'] if query['vignette_id'] == vignette_id]

###################################


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
    return list(itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1)))


def check_causality(theory, vignette, cause_variable, cause_value, effect_variable, effect_value):
    # only works for atomic  for now, both for cause and effect
    # therefore, AC3 is trivially satisfied

    print(vignette['name'] + ': ')

    ### preparation
    endo_variable_index = [index for index, item in enumerate(vignette['structural_equations']) if item is not None]
    exo_variable_index = [index for index, item in enumerate(vignette['structural_equations']) if item == None]
    variable_index = list(range(len(vignette['variables'])))
    cause_index = vignette['variables'].index(cause_variable)
    effect_index = vignette['variables'].index(effect_variable)

    ### AC1 is implied

    if theory == 'HP2015':
        print(f'According to {theory}, ', end='')
        ### AC2am
        # set x_prime != x
        # for now only check for one alternative value of x; should be for all but doesn't matter in binary setting
        x_prime = None
        for x in vignette['value_ranges'][cause_index]:
            if x != effect_value:
                x_prime = x

        for subset_w in powerset(set(variable_index)-{cause_index}):
            for i in exo_variable_index: # set exo variables to initial values
                vignette['current_values'][i] = vignette['initial_values'][i]
            for i in endo_variable_index: # reset endo variables
                vignette['current_values'][i] = None
            # print(subset_w) # uncomment to see subsets
            # set X=x' and W=w'
            for i in subset_w:
                vignette['current_values'][i] = vignette['initial_values'][i]
            vignette['current_values'][cause_index] = x_prime
            # propagate with newly set values
            for i in endo_variable_index:
                if i not in subset_w:
                    vignette['current_values'][i] = int(vignette['structural_equations'][i]())
            if vignette['current_values'][effect_index] != effect_value:
                # return True
                print(f'{cause_variable}={cause_value} IS an actual cause of {effect_variable}={effect_value}')
                print(f'Witness: W={[vignette["variables"][i] for i in subset_w]}, w={[vignette["current_values"][i] for i in subset_w]}, x\'={x_prime}')
                print('====================\n')
                break
        # return False
        else:
            print(f'{cause_variable}={cause_value} is NOT an actual cause of {effect_variable}={effect_value}')
            print('====================\n')

    elif theory == 'HP2005':
        pass

    else:
        raise ValueError('Invalid Theory')



def evaluate_on_all_vignettes(theory):
    vignettes = generate_vignettes()
    ff_conj = vignettes[0]
    ff_disj = vignettes[1]
    bottle_shatters = vignettes[2]
    check_causality(theory, ff_conj, 'ML', 1, 'FF', 1)  # True
    check_causality(theory, ff_disj, 'ML', 1, 'FF', 1)  # False
    check_causality(theory, bottle_shatters, 'ST', 1, 'BS', 1)  # True
    check_causality(theory, bottle_shatters, 'BT', 1, 'BS', 1)  # False



def evaluate_queries(vignettes, settings_json, queries_json):
    for vignette in vignettes:
        initial_values = get_initial_values_from_json(settings_json, vignette['vignette_id'])
        if initial_values:
            vignette['initial_values'] = [
                initial_values.get(var, 0) for var in vignette['variables']
            ]

        queries = get_queries_from_json(queries_json, vignette['vignette_id'])
        for query in queries:
            check_causality(
                'HP2015',
                vignette,
                query['query']['cause'],
                vignette['initial_values'][vignette['variables'].index(query['query']['cause'])],
                query['query']['effect'],
                vignette['initial_values'][vignette['variables'].index(query['query']['effect'])]
            )


if __name__ == '__main__':
    # ff_disj, ff_conj, bottle_shatters = generate_vignettes()
    vignettes = generate_vignettes_from_json(vignettes_json)
    evaluate_on_all_vignettes('HP2015')
    evaluate_queries(vignettes, settings_json, queries_json)

print()
