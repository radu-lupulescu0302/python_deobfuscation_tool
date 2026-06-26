import ast
import re

# ── patterns ──────────────────────────────────────────────────────────────────

_PATTERNS = {
    "URL":      re.compile(r'https?://[^\s"\'<>]{4,}|ftp://[^\s"\'<>]{4,}', re.I),
    "IPv4":     re.compile(r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'),
    "DOMAIN":   re.compile(r'\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+(?:com|net|org|io|ru|cn|tk|pw|top|xyz|info|biz|cc|su|onion)\b', re.I),
    "PATH_WIN": re.compile(r'[A-Za-z]:\\(?:[\w\-. ]+\\)*[\w\-. ]+', re.I),
    "PATH_UNIX":re.compile(r'(?<!["\w])/(?:etc|tmp|var|usr|home|root|bin|sbin|opt|proc|dev)/[\w./\-]+'),
    "REGISTRY": re.compile(r'\b(?:HKEY_[A-Z_]+|HK(?:LM|CU|CR|U|CC))\\[\w\\]+', re.I),
}

# Suspicious attribute calls to flag: module.func pairs
_SUSPICIOUS_MAP: dict[str, set[str]] = {
    "os":         {"system", "popen", "execv", "execve", "execvp", "spawn", "spawnl", "remove", "unlink", "rmdir"},
    "subprocess": {"Popen", "call", "run", "check_output", "getoutput"},
    "socket":     {"connect", "bind", "sendto", "send"},
    "shutil":     {"rmtree", "move", "copy", "copyfile"},
    "ctypes":     {"windll", "cdll", "WinDLL"},
    "urllib":     {"urlopen", "urlretrieve"},
    "requests":   {"get", "post", "put", "delete", "patch"},
    "winreg":     {"SetValueEx", "OpenKey", "CreateKey", "ConnectRegistry"},
}

# Bare dangerous builtins still present in output
_DANGEROUS_BUILTINS = {"eval", "exec", "compile", "__import__"}

# Suspicious method names regardless of which object they're called on
_SUSPICIOUS_METHODS = {"connect", "sendall", "sendto", "bind", "listen"}


class IOCExtractor:
    def __init__(self):
        self.hits: dict[str, list] = {k: [] for k in _PATTERNS}
        self.suspicious_calls: list[dict] = []

    def scan(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            # ── string constants ───────────────────────────────────────────
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self._match_string(node.value)

            # ── attribute calls: os.system(...) ───────────────────────────
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        mod = func.value.id
                        attr = func.attr
                        if mod in _SUSPICIOUS_MAP and attr in _SUSPICIOUS_MAP[mod]:
                            self._add_suspicious(f"{mod}.{attr}", getattr(node, "lineno", "?"))
                # suspicious method on any object: s.connect(), s.sendall(), ...
                if isinstance(func, ast.Attribute) and func.attr in _SUSPICIOUS_METHODS:
                    self._add_suspicious(f".{func.attr}()", getattr(node, "lineno", "?"))

                # bare eval / exec remaining in output
                if isinstance(func, ast.Name) and func.id in _DANGEROUS_BUILTINS:
                    self._add_suspicious(func.id + "()", getattr(node, "lineno", "?"))

    def _add_suspicious(self, text: str, line) -> None:
        if not any(e["text"] == text for e in self.suspicious_calls):
            self.suspicious_calls.append({"text": text, "line": line})

    def _match_string(self, s: str) -> None:
        for category, pattern in _PATTERNS.items():
            for match in pattern.finditer(s):
                value = match.group()
                # Deduplicate within each category
                if value not in self.hits[category]:
                    self.hits[category].append(value)

    def print_report(self) -> None:
        any_hit = any(self.hits.values()) or self.suspicious_calls
        print("\n=== IOC Report ===")
        if not any_hit:
            print("  No indicators found.")
            return

        for category, values in self.hits.items():
            seen = set()
            for v in values:
                # Normalise escape sequences before dedup
                normalised = v.replace('\\\\', '\\')
                if normalised not in seen:
                    seen.add(normalised)
                    print(f"  [{category:<10}] {normalised}")

        for entry in self.suspicious_calls:
            print(f"  [SUSPICIOUS ] {entry['text']}  (line {entry['line']})")
