import ast

# Makes you wish you had CLOS-style generic functions

def ensure_good_tree(ast_tree):
    # Makes you wish you had a typecase or etypecase :/
    if isinstance(ast_tree, ast.Constant):
        return True
    if isinstance(ast_tree, ast.Name):
        return True
    elif isinstance(ast_tree, ast.UnaryOp):
        arg = ast_tree.operand
        return ensure_good_tree(arg)
    elif isinstance(ast_tree, ast.BoolOp):
        args = ast_tree.values
        return all(map(ensure_good_tree, args))
    elif isinstance(ast_tree, ast.BinOp):
        return ensure_good_tree(ast_tree.left) and ensure_good_tree(ast_tree.right)
    elif isinstance(ast_tree, ast.Compare):
        return ensure_good_tree(ast_tree.left) and \
            all(map(ensure_good_tree, ast_tree.comparators))
    else:
        return False


class NameToDictSubscript(ast.NodeTransformer):
    def __init__(self, var_name):
        self.var_name = var_name

    def visit_Name(self, node):
        return ast.Subscript(
            value=ast.Name(id=self.var_name, ctx=ast.Load()),
            slice=ast.Constant(value=node.id),
            ctx=node.ctx
        )

def rewrite_tree_with_dict(ast_tree, var_name):
    tree_copy = ast.parse(ast.unparse(ast_tree), mode="eval").body
    new_tree = NameToDictSubscript(var_name).visit(tree_copy)
    ast.fix_missing_locations(new_tree)
    try:
        return ast.unparse(new_tree)
    except Exception:
        return False

def sanitize_and_parse(expr_string, print_eqn=False):
    """

    Sanitizes the input to ensure that it is only an expression of variables
    as defined by ensure_good_tree above.

    This (should) avoid spurious calls such as to
      "import os; os.run('cat credentials_file | curl -X post'); os.run('rm -rf ~')"
    etc

    Example:

    parse_sanitize("C", "A and B")
      -> eval("def C(values): return values['A'] and values['B']")

    """

    whole = ast.parse(expr_string)
    if len(whole.body) != 1:
        raise Exception("Malformed expr_string:", expr_string)
    body = whole.body[0]
    if not isinstance(body, ast.Expr):
        raise Exception("Malformed expr_string, unexpected parsed body type:", type(body), expr_string)

    success = ensure_good_tree(body.value)
    if not success:
        raise Exception("Malformed expr_string; could not ensure good tree:", expr_string)

    expr_restring = rewrite_tree_with_dict(body.value, "values")
    if not expr_restring:
        raise Exception("Malformed expr_string; could not rewrite as fn body, possibly unknown op:", expr_string)

    fn_str = "lambda values: {}".format(expr_restring)
    if print_eqn: print(fn_str)

    return eval(fn_str)

if __name__ == "__main__":
    fn = parse_sanitized("A and B")
    print(fn)
    print(fn({"A": 1, "B": 0}))
    print(fn({"A": 1, "B": 1}))
