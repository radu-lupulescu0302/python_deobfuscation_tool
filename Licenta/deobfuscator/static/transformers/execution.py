import ast
from ..utils import is_constant
from .base import BaseTransformer
from ...stats import record


class ExecutionTransformer(BaseTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        # compile(src_const, filename, mode) → src_const
        # Unwrapping lets ConstantPropagation + ExecutionTransformer inline
        # the payload on the next iteration: exec(compile(src)) → exec(src) → inlined
        if (isinstance(node.func, ast.Name)
                and node.func.id == 'compile'
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, (str, bytes))):
            src = node.args[0].value
            if isinstance(src, bytes):
                try:
                    src = src.decode('utf-8', errors='ignore')
                except Exception:
                    return node
            print(f"    [Execution] compile(src, ...) unwrapped ({len(src)} chars)")
            record("compile() wrapping")
            return ast.Constant(value=src)
        return node

    def visit_Expr(self, node):
        self.generic_visit(node)

        # Only handle top-level exec(...) / eval(...) statements
        if not (isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id in ("exec", "eval")):
            return node

        call = node.value
        if not (call.args and is_constant(call.args[0])):
            return node

        payload = call.args[0].value
        if isinstance(payload, bytes):
            try:
                payload = payload.decode("utf-8", errors="ignore")
            except Exception:
                return node

        if not isinstance(payload, str) or not payload.strip():
            return node

        try:
            inner_tree = ast.parse(payload)
            print(f"    [Execution] Inlined exec() payload ({len(payload)} chars)")
            record("exec()/eval() inlining")
            return inner_tree.body  # list of statements replaces this Expr
        except SyntaxError:
            # Payload isn't valid Python — keep it as a readable comment
            print(f"    [Execution] exec() payload not valid Python, keeping as comment")
            return ast.Expr(value=ast.Constant(value=f"# exec payload: {payload}"))
