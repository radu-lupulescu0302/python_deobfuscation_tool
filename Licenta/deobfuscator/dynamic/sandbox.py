import importlib
import threading

# Modules that are safe to import inside a sandbox exec
_SAFE_MODULES = frozenset({
    'base64', 'zlib', 'binascii', 'codecs', 'hashlib',
    'struct', 'string', 'math', 'itertools', 'functools',
    'collections', 'operator', 'io', 'json', 're',
})


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split('.')[0]
    if root not in _SAFE_MODULES:
        raise ImportError(f"Import of '{name}' is blocked in the sandbox")
    return importlib.import_module(name)


_SAFE_BUILTINS = {
    '__import__': _safe_import,
    'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
    'bytearray': bytearray, 'bytes': bytes, 'callable': callable,
    'chr': chr, 'dict': dict, 'divmod': divmod,
    'enumerate': enumerate, 'filter': filter, 'float': float,
    'format': format, 'frozenset': frozenset, 'getattr': getattr,
    'hasattr': hasattr, 'hash': hash, 'hex': hex, 'int': int,
    'isinstance': isinstance, 'issubclass': issubclass, 'iter': iter,
    'len': len, 'list': list, 'map': map, 'max': max, 'min': min,
    'next': next, 'oct': oct, 'ord': ord, 'pow': pow, 'print': print,
    'range': range, 'repr': repr, 'reversed': reversed, 'round': round,
    'set': set, 'slice': slice, 'sorted': sorted, 'str': str,
    'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
}


class SafeSandbox:
    def _make_ns(self):
        """
        Return a fresh namespace for exec.

        Using a *single* dict for both globals and locals is intentional:
        lambdas defined in exec'd code capture free variables from the
        enclosing frame.  With separate globals/locals the free-variable
        lookup goes to globals (empty), causing NameError.  A single shared
        namespace avoids this.
        """
        return {'__builtins__': _SAFE_BUILTINS}

    def safe_exec(self, code: str, timeout: int = 5):
        """Execute code and return success/error.  Legacy helper."""
        return self.safe_exec_and_extract(code, timeout=timeout)

    def safe_exec_and_extract(self, code: str, var_name: str = None, timeout: int = 5):
        """
        Execute *code* in a sandboxed namespace and extract *var_name*.

        Returns a dict with keys:
            success  – bool
            value    – the value of var_name (or None)
            locals   – all non-dunder variables set during execution
            error    – error string if success is False
        """
        result = {"success": False, "value": None, "locals": {}, "error": None}

        def _run():
            ns = self._make_ns()
            try:
                exec(compile(code, "<sandbox>", "exec"), ns)
                result["success"] = True
                result["locals"] = {k: v for k, v in ns.items()
                                    if not k.startswith('__')}
                if var_name is not None:
                    result["value"] = ns.get(var_name)
            except Exception as exc:
                result["error"] = str(exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            result["error"] = "timeout"
        return result

    def safe_exec_code_object(self, code_obj, timeout: int = 5):
        """
        Execute a marshal'd code object in the sandbox and capture stdout.

        Returns {"success": True, "output": captured_stdout} or {"success": False}.
        """
        import io
        result = {"success": False, "output": "", "error": None}

        def _run():
            buf = io.StringIO()
            ns = self._make_ns()
            builtins = dict(_SAFE_BUILTINS)
            builtins['print'] = lambda *a, **kw: buf.write(' '.join(str(x) for x in a) + '\n')
            ns['__builtins__'] = builtins
            try:
                exec(code_obj, ns)
                result["success"] = True
                result["output"] = buf.getvalue()
                result["locals"] = {k: v for k, v in ns.items()
                                    if not k.startswith('__') and isinstance(v, (str, int, float, bytes, bool))}
            except Exception as exc:
                result["error"] = str(exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            result["error"] = "timeout"
        return result
