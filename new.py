class Variable:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value
        self.parents = []
        self.equation = None

    def set_equation(self, equation):
        self.equation = equation

    def add_parent(self, parent):
        self.parents.append(parent)

    def evaluate(self):
        if self.equation:
            self.value = self.equation()

class StructuralEquationModel:
    def __init__(self):
        self.variables = {}

    def add_variable(self, variable):
        self.variables[variable.name] = variable

    def set_equation(self, variable_name, equation):
        variable = self.variables[variable_name]
        variable.set_equation(equation)

    def evaluate(self):
        # Evaluate each variable in an appropriate order
        evaluated = set()
        def evaluate_variable(var):
            for parent in var.parents:
                if parent.name not in evaluated:
                    evaluate_variable(self.variables[parent.name])
            var.evaluate()
            evaluated.add(var.name)

        for var in self.variables.values():
            if var.name not in evaluated:
                evaluate_variable(var)

class CausationEvaluator:
    def __init__(self, model):
        self.model = model

    def intervene(self, variable_name, value):
        # Set the variable to a specific value and re-evaluate the model
        self.model.variables[variable_name].value = value
        self.model.evaluate()

    def check_counterfactual(self, cause, effect):
        # Implement the logic to check counterfactual dependency
        original_value = self.model.variables[effect].value

        # Intervene on the cause
        self.intervene(cause, not self.model.variables[cause].value)

        # Check if the effect changes
        result = self.model.variables[effect].value != original_value

        # Revert the intervention
        self.intervene(cause, not self.model.variables[cause].value)

        return result

    def is_actual_cause(self, cause, effect):
        # Check the definition of actual causation
        return self.check_counterfactual(cause, effect)

# Create the structural equation model
model = StructuralEquationModel()

# Define variables
ST = Variable('ST', value=1)  # Suzy throws
SH = Variable('SH')           # Suzy's hit
BT = Variable('BT', value=1)  # Billy throws
BH = Variable('BH')           # Billy's hit
BS = Variable('BS')           # Bottle shatters

# Add variables to the model
model.add_variable(ST)
model.add_variable(SH)
model.add_variable(BT)
model.add_variable(BH)
model.add_variable(BS)

# Define equations
model.set_equation('SH', lambda: model.variables['ST'].value)
model.set_equation('BH', lambda: model.variables['BT'].value and not model.variables['SH'].value)
model.set_equation('BS', lambda: model.variables['SH'].value or model.variables['BH'].value)

# Establish causal relationships (this helps in manual evaluation order if needed)
SH.add_parent(ST)
BH.add_parent(BT)
BH.add_parent(SH)
BS.add_parent(SH)
BS.add_parent(BH)

# Evaluate the model initially
model.evaluate()

# Create causation evaluator
evaluator = CausationEvaluator(model)

# Check actual causation
print("Is ST an actual cause of BS?", evaluator.is_actual_cause('ST', 'BS'))  # Should output True
print("Is BT an actual cause of BS?", evaluator.is_actual_cause('BT', 'BS'))  # Should output False if ST preempts BT
