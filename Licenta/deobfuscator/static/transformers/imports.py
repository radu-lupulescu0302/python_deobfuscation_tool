import ast
from .base import BaseTransformer
from ...stats import record

class ImportsTransformer(BaseTransformer):
    """
    Resolve __import__ calls and normalise aliased imports.

    Aliased imports like `import base64 as _b64` hide the canonical module
    name from downstream transformers that pattern-match on it.  This
    transformer rewrites every aliased name back to the canonical one so
    that e.g. EncodingsTransformer can recognise `base64.b64decode`.
    """

    def __init__(self):
        super().__init__()
        self._modules_to_import: set[str] = set()
        # alias → canonical  e.g. {"_b64": "base64"}
        self._alias_map: dict[str, str] = {}

    # ── first pass: collect aliases from import statements ─────────────────

    def _collect_aliases(self, stmts: list) -> None:
        for stmt in stmts:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    if alias.asname and alias.asname != alias.name:
                        canonical = alias.name.split('.')[0]
                        self._alias_map[alias.asname] = canonical

    # ── normalise import statements themselves ─────────────────────────────

    def _normalise_imports(self, stmts: list) -> list:
        out = []
        for stmt in stmts:
            if isinstance(stmt, ast.Import):
                new_names = []
                for alias in stmt.names:
                    if alias.asname and alias.asname in self._alias_map:
                        print(f"    [Imports] Normalised 'import {alias.name} as {alias.asname}' -> 'import {alias.name}'")
                        record("import alias obfuscation")
                        new_names.append(ast.alias(name=alias.name))
                    else:
                        new_names.append(alias)
                stmt.names = new_names
            out.append(stmt)
        return out

    # ── replace aliased Name nodes with the canonical name ─────────────────

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self._alias_map:
            canonical = self._alias_map[node.id]
            print(f"    [Imports] Replaced alias '{node.id}' -> '{canonical}'")
            return ast.Name(id=canonical, ctx=ast.Load())
        return node

    # ── resolve __import__('module') calls ─────────────────────────────────

    def visit_Call(self, node):
        self.generic_visit(node)

        if (isinstance(node.func, ast.Name)
                and node.func.id == "__import__"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            module_name = node.args[0].value
            self._modules_to_import.add(module_name)
            print(f"    [Imports] __import__('{module_name}') -> Name '{module_name}'")
            record("__import__() call")
            return ast.Name(id=module_name, ctx=ast.Load())

        return node

    # ── module-level orchestration ─────────────────────────────────────────

    def visit_Module(self, node):
        self._collect_aliases(node.body)
        node.body = self._normalise_imports(node.body)

        # Run child visitors (visit_Name, visit_Call) with alias map populated
        self.generic_visit(node)

        # Collect names that are already imported
        already_imported: set[str] = set()
        for stmt in node.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    already_imported.add(alias.asname or alias.name.split('.')[0])
            elif isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    already_imported.add(alias.asname or alias.name)

        # Inject import statements for modules resolved via __import__
        missing = self._modules_to_import - already_imported
        if missing:
            new_imports = [
                ast.Import(names=[ast.alias(name=mod)])
                for mod in sorted(missing)
            ]
            for mod in sorted(missing):
                print(f"    [Imports] Injected 'import {mod}'")
            node.body = new_imports + node.body

        return node
