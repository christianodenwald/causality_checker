from typing import List

###

class Variable:
    def __init__(self, name:str, range:List, value:int, exo=False):
        self.name = name
        self.range = range
        self.value = value
        self.exo = exo

class Signature:
    def __init__(self):
        self.variables = []

    def add_variable(self, variable:Variable):
        self.variables.append[variable]

class CausalModel:
    def __init__(self, signature:Signature, equations):
        self.signature = signature
        self.equations = equations
        self.variables = signature.variables


class Theory:
    def __init__(self, theory):
        self.theory = theory


class Example:
    def __init__(self, model:CausalModel):
        self.model = model

    def evaluate_variable_under_theory(self, theory:Theory, variable):
        pass

    def evaluate_all_variables(self, theory:Theory):
        for variable in self.variables:
            self.evaluate_variable_under_theory(self, theory, variable)






#### copy from java code

class CausalModel():
    def __init__(self, name, equations, exovariables, endovariables, checkvalidity):
        self.name = name
        self.is_valid = self.validitycheck(self)

    def validitycheck(self):
        pass



wildfire_sign = Signature()
wildfire_sign.add_variable()

wildfire = CausalModel()
wildfire_conj = Example(wildfire, )