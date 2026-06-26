import ast
from ..utils import is_constant
from .base import BaseTransformer
from ...stats import record


class ConstantPropagationTransformer(BaseTransformer):
    """
    Tracks simple var = <constant> assignments and substitutes the constant
    wherever that variable is later read (Load context).

    This lets downstream transformers resolve patterns like:
        dec = xor_fn(encoded)   # XOR transformer turns this into dec = "..."
        exec(dec)               # becomes exec("...") after propagation
    """

    def __init__(self):
        super().__init__()
        self._env: dict = {}       # var_name -> constant_value
        self._name_env: dict = {}  # var_name -> target_name (module/name aliases)

    def visit_Assign(self, node):
        # Visit RHS first so any Name refs there are substituted before we record
        self.generic_visit(node)
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if is_constant(node.value):
                self._env[name] = node.value.value
                self._name_env.pop(name, None)
            elif isinstance(node.value, ast.Name):
                self._name_env[name] = node.value.id
                self._env.pop(name, None)
            else:
                # Re-assignment to non-constant invalidates previous entries
                self._env.pop(name, None)
                self._name_env.pop(name, None)
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            if node.id in self._env:
                print(f"    [Propagation] Substituted '{node.id}' -> {self._env[node.id]!r}")
                record("constant propagation")
                return ast.Constant(value=self._env[node.id])
            if node.id in self._name_env:
                target = self._name_env[node.id]
                print(f"    [Propagation] Substituted alias '{node.id}' -> '{target}'")
                record("module alias propagation")
                return ast.Name(id=target, ctx=ast.Load())
        return node
