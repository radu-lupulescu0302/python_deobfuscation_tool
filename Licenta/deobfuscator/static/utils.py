import ast

def is_constant(node):
    return isinstance(node, ast.Constant)

def get_constant_value(node):
    return node.value if is_constant(node) else None

def is_attr_call(node, module: str, func: str):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    return (isinstance(node.func.value, ast.Name) and 
            node.func.value.id == module and 
            node.func.attr == func)