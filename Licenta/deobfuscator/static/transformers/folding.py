import ast
from .base import BaseTransformer
from ...stats import record


class FoldingTransformer(BaseTransformer):
    """Constant folding + basic dead-code removal."""

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if not (isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant)):
            return node
        l, r = node.left.value, node.right.value
        try:
            if isinstance(node.op, ast.Add):
                record("constant folding")
                return ast.Constant(value=l + r)
            if isinstance(node.op, ast.Sub):
                if isinstance(l, (int, float)) and isinstance(r, (int, float)):
                    return ast.Constant(value=l - r)
            if isinstance(node.op, ast.Mult):
                if isinstance(l, (int, float)) and isinstance(r, (int, float)):
                    return ast.Constant(value=l * r)
                if isinstance(l, str) and isinstance(r, int):
                    return ast.Constant(value=l * r)
                if isinstance(l, int) and isinstance(r, str):
                    return ast.Constant(value=l * r)
            if isinstance(node.op, ast.FloorDiv):
                if isinstance(l, (int, float)) and isinstance(r, (int, float)) and r != 0:
                    return ast.Constant(value=l // r)
            if isinstance(node.op, ast.Mod):
                if isinstance(l, (int, float)) and isinstance(r, (int, float)) and r != 0:
                    return ast.Constant(value=l % r)
            if isinstance(node.op, ast.Pow):
                if isinstance(l, (int, float)) and isinstance(r, (int, float)):
                    result = l ** r
                    if abs(result) < 10 ** 18:  # guard against huge numbers
                        return ast.Constant(value=result)
            if isinstance(node.op, ast.BitXor):
                if isinstance(l, int) and isinstance(r, int):
                    return ast.Constant(value=l ^ r)
            if isinstance(node.op, ast.BitOr):
                if isinstance(l, int) and isinstance(r, int):
                    return ast.Constant(value=l | r)
            if isinstance(node.op, ast.BitAnd):
                if isinstance(l, int) and isinstance(r, int):
                    return ast.Constant(value=l & r)
            if isinstance(node.op, ast.LShift):
                if isinstance(l, int) and isinstance(r, int) and 0 <= r < 64:
                    return ast.Constant(value=l << r)
            if isinstance(node.op, ast.RShift):
                if isinstance(l, int) and isinstance(r, int) and r >= 0:
                    return ast.Constant(value=l >> r)
        except Exception:
            pass
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if not isinstance(node.operand, ast.Constant):
            return node
        v = node.operand.value
        try:
            if isinstance(node.op, ast.USub) and isinstance(v, (int, float)):
                return ast.Constant(value=-v)
            if isinstance(node.op, ast.UAdd) and isinstance(v, (int, float)):
                return ast.Constant(value=+v)
            if isinstance(node.op, ast.Invert) and isinstance(v, int):
                return ast.Constant(value=~v)
            if isinstance(node.op, ast.Not):
                return ast.Constant(value=not v)
        except Exception:
            pass
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        # getattr(obj, 'attr') → obj.attr
        if (isinstance(node.func, ast.Name)
                and node.func.id == 'getattr'
                and len(node.args) == 2
                and not node.keywords
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
                and node.args[1].value.isidentifier()):
            attr = node.args[1].value
            print(f"    [Folding] getattr(..., {attr!r}) -> .{attr}")
            record("getattr() resolution")
            return ast.Attribute(value=node.args[0], attr=attr, ctx=ast.Load())
        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if not isinstance(node.value, ast.Constant):
            return node
        val = node.value.value
        if not isinstance(val, (str, bytes)):
            return node
        try:
            # Simple index: s[i]
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                result = val[node.slice.value]
                print(f"    [Folding] Subscript index -> {result!r}")
                return ast.Constant(value=result)
            # Slice: s[start:stop:step]
            if isinstance(node.slice, ast.Slice):
                s = node.slice
                def _int_or_none(n):
                    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, int) else None if n is None else ...
                lo = _int_or_none(s.lower)
                hi = _int_or_none(s.upper)
                st = _int_or_none(s.step)
                if ... not in (lo, hi, st):
                    result = val[lo:hi:st]
                    print(f"    [Folding] Subscript slice -> {result!r}")
                    record("string slice")
                    return ast.Constant(value=result)
        except Exception:
            pass
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant):
            if not node.test.value:
                return node.orelse  # keep else block
            else:
                return node.body    # keep if block
        return node
