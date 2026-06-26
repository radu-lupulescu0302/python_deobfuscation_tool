import ast
from .sandbox import SafeSandbox
from .memory_dumper import MemoryDumper


def _extract_co_strings(code_obj) -> list[str]:
    """Recursively collect non-empty string constants from a code object."""
    results = []
    for c in code_obj.co_consts:
        if isinstance(c, str) and c.strip() and not c.startswith('<'):
            results.append(c)
        elif hasattr(c, 'co_consts'):
            results.extend(_extract_co_strings(c))
    return results


class ExecutionHooks:
    def __init__(self):
        self.sandbox = SafeSandbox()
        self.dumper = MemoryDumper()

    # ── site discovery ─────────────────────────────────────────────────────

    def find_execution_sites(self, tree):
        """
        Return a list of dicts describing every remaining exec/eval statement.

        We track the *Expr statement* (not the inner Call) so that
        _replace_node can swap the whole statement for inlined code.
        """
        sites = []

        class Visitor(ast.NodeVisitor):
            def visit_Expr(self, node):
                if (isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id in ("exec", "eval")):
                    call = node.value
                    arg = call.args[0] if call.args else None
                    sites.append({
                        "node": node,          # Expr — used for replacement
                        "call": call,          # Call — for reference
                        "arg": arg,
                        "lineno": getattr(node, "lineno", 0),
                    })
                self.generic_visit(node)

        Visitor().visit(tree)
        return sites

    # ── site processing ────────────────────────────────────────────────────

    def process_site(self, site, tree):
        """
        Try to recover the payload for one exec/eval site.

        Strategy
        --------
        1. If the argument is already a constant (shouldn't reach the dynamic
           phase normally, but handle it gracefully).
        2. If the argument is a variable name, extract the minimal program
           slice that computes that variable and execute it in the sandbox.
        3. Return {"success": True, "new_node": list_of_stmts} on success.
        """
        arg = site["arg"]

        # ── constant arg (fallback) ────────────────────────────────────────
        if isinstance(arg, ast.Constant):
            payload = arg.value
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="ignore")
            return self._payload_to_result(payload, site)

        # ── marshal.loads(bytes_const) arg ────────────────────────────────
        if (isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Attribute)
                and isinstance(arg.func.value, ast.Name)
                and arg.func.value.id == "marshal"
                and arg.func.attr == "loads"
                and arg.args
                and isinstance(arg.args[0], ast.Constant)
                and isinstance(arg.args[0].value, bytes)):
            import marshal as _marshal
            print(f"    [Dynamic] Processing marshal.loads payload")
            try:
                code_obj = _marshal.loads(arg.args[0].value)
                # Run in sandbox and capture namespace + stdout
                result = self.sandbox.safe_exec_code_object(code_obj)
                if result.get("success"):
                    # Reconstruct assignments from captured namespace
                    lines = []
                    for k, v in result.get("locals", {}).items():
                        lines.append(f"{k} = {v!r}")
                    stdout = result.get("output", "").strip()
                    if stdout:
                        for line in stdout.splitlines():
                            lines.append(f"# output: {line}")
                    if lines:
                        payload = "\n".join(lines)
                        print(f"    [Dynamic] Recovered marshal payload ({len(lines)} statements)")
                        return self._payload_to_result(payload, site)
                # Fallback: extract string constants from code object
                strings = _extract_co_strings(code_obj)
                if strings:
                    comment = "# marshal payload strings: " + ", ".join(repr(s) for s in strings[:10])
                    node = ast.Expr(value=ast.Constant(value=comment))
                    print(f"    [Dynamic] Extracted {len(strings)} string constants from marshal payload")
                    return {"success": True, "new_node": [node]}
            except Exception as e:
                print(f"    [Dynamic] marshal.loads sandbox error: {e}")
            return {"success": False}

        # ── variable arg — extract slice and execute ───────────────────────
        if isinstance(arg, ast.Name):
            var_name = arg.id
            print(f"    [Dynamic] Resolving variable '{var_name}' via slice execution")

            slice_src = self._extract_slice(var_name, site["node"], tree)
            if slice_src is None:
                print(f"    [Dynamic] Could not build slice for '{var_name}'")
                return {"success": False}

            result = self.sandbox.safe_exec_and_extract(slice_src, var_name)
            if not result["success"]:
                print(f"    [Dynamic] Sandbox error: {result['error']}")
                return {"success": False}

            payload = result["value"]
            if payload is None:
                print(f"    [Dynamic] '{var_name}' was not set after slice execution")
                return {"success": False}

            print(f"    [Dynamic] Recovered '{var_name}' = {payload!r}")
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="ignore")
            return self._payload_to_result(payload, site)

        print(f"    [Dynamic] Unsupported exec argument type: {type(arg).__name__}")
        return {"success": False}

    # ── slice extraction ───────────────────────────────────────────────────

    def _extract_slice(self, var_name: str, exec_stmt, tree):
        """
        Build the minimal program slice that computes *var_name*.

        Collects all import statements and assignments (transitively needed
        to compute var_name) that appear before *exec_stmt* in the module
        body, then unparses them to source.
        """
        # Gather statements that appear before the exec in the module body
        prior = []
        for stmt in tree.body:
            if stmt is exec_stmt:
                break
            prior.append(stmt)

        if not prior:
            return None

        # Compute the transitive set of variables needed
        needed = self._transitive_deps(var_name, prior)

        # Build the slice: imports + assignments for needed vars
        slice_stmts = []
        for stmt in prior:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                slice_stmts.append(stmt)
            elif (isinstance(stmt, ast.Assign)
                  and len(stmt.targets) == 1
                  and isinstance(stmt.targets[0], ast.Name)
                  and stmt.targets[0].id in needed):
                slice_stmts.append(stmt)

        if not slice_stmts:
            return None

        mod = ast.Module(body=slice_stmts, type_ignores=[])
        ast.fix_missing_locations(mod)
        return ast.unparse(mod)

    def _transitive_deps(self, var_name: str, stmts):
        """
        Return the set of all variable names transitively required to
        compute *var_name* from the given list of assignment statements.
        """
        needed = {var_name}
        changed = True
        while changed:
            changed = False
            for stmt in stmts:
                if not (isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)):
                    continue
                if stmt.targets[0].id not in needed:
                    continue
                for node in ast.walk(stmt.value):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        if node.id not in needed:
                            needed.add(node.id)
                            changed = True
        return needed

    # ── shared helper ──────────────────────────────────────────────────────

    def _payload_to_result(self, payload, site):
        """Parse a string payload and return a replacement node list."""
        if not isinstance(payload, str) or not payload.strip():
            return {"success": False}
        try:
            inner = ast.parse(payload)
            if not inner.body:
                return {"success": False}
            print(f"    [Dynamic] Inlining payload ({len(payload)} chars) "
                  f"at line {site['lineno']}")
            return {"success": True, "new_node": inner.body}
        except SyntaxError:
            print(f"    [Dynamic] Payload is not valid Python — keeping as comment")
            comment = ast.Expr(value=ast.Constant(value=f"# exec payload: {payload}"))
            return {"success": True, "new_node": [comment]}
