import ast
from ..utils import is_constant
from .base import BaseTransformer
from ...stats import record


class XorArithmeticTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self._xor_fns = {}  # var_name -> xor_key

    # ── lambda registration ────────────────────────────────────────────────

    def visit_Assign(self, node):
        self.generic_visit(node)
        if (len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Lambda)):
            key = self._extract_xor_key(node.value)
            if key is not None:
                name = node.targets[0].id
                self._xor_fns[name] = key
                record("XOR cipher lambda")
                print(f"    [XOR] Registered lambda '{name}' with key={key}")
        return node

    # ── call resolution ────────────────────────────────────────────────────

    def visit_Call(self, node):
        self.generic_visit(node)

        # Known XOR lambda call: fn(string_const)
        if (isinstance(node.func, ast.Name)
                and node.func.id in self._xor_fns
                and node.args
                and is_constant(node.args[0])):
            text = node.args[0].value
            if isinstance(text, str):
                key = self._xor_fns[node.func.id]
                decoded = ''.join(chr(ord(c) ^ key) for c in text)
                print(f"    [XOR] Decoded '{node.func.id}(...)' -> {decoded!r}")
                record("XOR cipher lambda")
                return ast.Constant(value=decoded)

        # Inline ''.join(chr(ord(c) ^ KEY) for/list c in const_str)
        if self._is_join_xor_call(node):
            result = self._eval_join_xor(node)
            if result is not None:
                print(f"    [XOR] Inlined join-XOR -> {result!r}")
                record("XOR join (inline)")
                return ast.Constant(value=result)

        return node

    # ── helpers ────────────────────────────────────────────────────────────

    def _extract_xor_key(self, lambda_node):
        """Return the integer XOR key found anywhere inside a lambda, or None."""
        for n in ast.walk(lambda_node):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitXor):
                for side in (n.left, n.right):
                    if isinstance(side, ast.Constant) and isinstance(side.value, int):
                        return side.value
        return None

    def _is_join_xor_call(self, node):
        """True for ''.join(gen/listcomp) where the element uses chr(... ^ int)."""
        if not (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Constant)
                and node.func.value.value == ""
                and node.func.attr == "join"):
            return False
        if not node.args:
            return False
        return isinstance(node.args[0], (ast.GeneratorExp, ast.ListComp))

    def _eval_join_xor(self, node):
        """Evaluate join-XOR comprehensions when fully constant."""
        inner = node.args[0]
        if len(inner.generators) != 1:
            return None
        gen = inner.generators[0]
        if not isinstance(gen.target, ast.Name):
            return None

        # Case 1: ''.join(chr(ord(c) ^ KEY) for c in "string")
        if is_constant(gen.iter) and isinstance(gen.iter.value, str):
            key = self._extract_join_xor_key(inner.elt, gen.target)
            if key is None:
                return None
            try:
                return ''.join(chr(ord(c) ^ key) for c in gen.iter.value)
            except Exception:
                return None

        # Case 2: ''.join(chr(x ^ KEY) for x in [int, ...])
        if (isinstance(gen.iter, ast.List)
                and all(isinstance(e, ast.Constant) and isinstance(e.value, int)
                        for e in gen.iter.elts)):
            key = self._extract_join_xor_key_int(inner.elt, gen.target)
            if key is None:
                return None
            try:
                return ''.join(chr(e.value ^ key) for e in gen.iter.elts)
            except Exception:
                return None

        return None

    def _extract_join_xor_key_int(self, elt, target):
        """Return key if elt is chr(target ^ key) or chr(key ^ target) (no ord())."""
        if not (isinstance(elt, ast.Call)
                and isinstance(elt.func, ast.Name)
                and elt.func.id == "chr"
                and len(elt.args) == 1):
            return None
        inner = elt.args[0]
        if not (isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.BitXor)):
            return None

        def is_target_name(n):
            return isinstance(n, ast.Name) and n.id == target.id

        if is_target_name(inner.left) and isinstance(inner.right, ast.Constant) and isinstance(inner.right.value, int):
            return inner.right.value
        if is_target_name(inner.right) and isinstance(inner.left, ast.Constant) and isinstance(inner.left.value, int):
            return inner.left.value
        return None

    def _extract_join_xor_key(self, elt, target):
        """Return key if elt is chr(ord(target) ^ key) or chr(key ^ ord(target))."""
        if not (isinstance(elt, ast.Call)
                and isinstance(elt.func, ast.Name)
                and elt.func.id == "chr"
                and len(elt.args) == 1):
            return None
        inner = elt.args[0]
        if not (isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.BitXor)):
            return None

        def is_ord_of_target(n):
            return (isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == "ord"
                    and len(n.args) == 1
                    and isinstance(n.args[0], ast.Name)
                    and n.args[0].id == target.id)

        if is_ord_of_target(inner.left) and isinstance(inner.right, ast.Constant) and isinstance(inner.right.value, int):
            return inner.right.value
        if is_ord_of_target(inner.right) and isinstance(inner.left, ast.Constant) and isinstance(inner.left.value, int):
            return inner.left.value
        return None
