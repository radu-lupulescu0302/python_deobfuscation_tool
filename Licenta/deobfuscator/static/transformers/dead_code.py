import ast
from .base import BaseTransformer
from ..utils import is_constant
from ...stats import record


class DeadCodeTransformer(BaseTransformer):
    """
    Remove dead imports and unused simple-assignment variables.

    An import is dead when none of its bound names appear in Load context
    anywhere in the same scope.  An assignment is dead when its target name
    never appears in Load context in the same scope.

    Runs last in each pipeline iteration so earlier transformers (folding,
    propagation, execution inlining) have already shrunk the reference set.
    Cascades automatically across pipeline iterations: removing one dead
    assignment often makes another dead on the next pass.
    """

    def visit_Module(self, node):
        self.generic_visit(node)
        node.body = self._clean(node.body)
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        node.body = self._clean(node.body)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    # ── core ──────────────────────────────────────────────────────────────

    def _has_unresolved_exec(self, stmts):
        """Return True if any exec()/eval() call has a non-constant argument."""
        for stmt in stmts:
            for node in ast.walk(stmt):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id in ('exec', 'eval')
                        and node.args
                        and not is_constant(node.args[0])):
                    return True
        return False

    def _clean(self, stmts):
        if self._has_unresolved_exec(stmts):
            return stmts
        used = self._loaded_names(stmts)
        out = []
        for stmt in stmts:
            if self._is_dead_import(stmt, used):
                print(f"    [DeadCode] Removed import: {ast.unparse(stmt)}")
                record("dead code removal")
                continue
            if self._is_dead_assign(stmt, used):
                print(f"    [DeadCode] Removed dead var '{stmt.targets[0].id}'")
                record("dead code removal")
                continue
            out.append(stmt)
        return out

    def _loaded_names(self, stmts):
        """Collect every Name used in Load context across all statements."""
        names = set()
        for stmt in stmts:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    names.add(node.id)
        return names

    def _is_dead_import(self, stmt, used):
        if isinstance(stmt, ast.Import):
            return all(
                (alias.asname or alias.name.split(".")[0]) not in used
                for alias in stmt.names
            )
        if isinstance(stmt, ast.ImportFrom):
            return all(
                (alias.asname or alias.name) not in used
                for alias in stmt.names
            )
        return False

    def _is_dead_assign(self, stmt, used):
        if not isinstance(stmt, ast.Assign):
            return False
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            return False
        return stmt.targets[0].id not in used
