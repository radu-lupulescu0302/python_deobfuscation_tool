import ast

class BaseTransformer(ast.NodeTransformer):
    """Improved helper methods"""

    def _is_attr_call(self, node, module_name: str, func_name: str):
        """Check for module.func(...) pattern"""
        if not isinstance(node, ast.Call):
            return False
        if not isinstance(node.func, ast.Attribute):
            return False
        
        attr = node.func
        # Check if it's base64.b64decode style
        if isinstance(attr.value, ast.Name) and attr.value.id == module_name and attr.attr == func_name:
            return True
        return False