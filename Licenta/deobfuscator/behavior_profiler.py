from __future__ import annotations
from .ioc_extractor import IOCExtractor

_RULES: list[dict] = [
    {
        "tag": "C2 BEACONING",
        "desc": "Communicates with a remote server (URL/IP + network call)",
        "check": lambda ioc, _: (bool(ioc.hits["URL"] or ioc.hits["IPv4"]))
                  and any(e["text"] in {".connect()", "socket.connect", "socket.bind",
                                        "requests.get", "requests.post", "urllib.urlopen"}
                          for e in ioc.suspicious_calls),
    },
    {
        "tag": "PERSISTENCE",
        "desc": "Survives reboots via registry Run key or startup path",
        "check": lambda ioc, _: bool(ioc.hits["REGISTRY"]),
    },
    {
        "tag": "FILE DROPPER",
        "desc": "References or writes executable paths on disk",
        "check": lambda ioc, _: bool(ioc.hits["PATH_WIN"] or ioc.hits["PATH_UNIX"]),
    },
    {
        "tag": "PROCESS EXECUTION",
        "desc": "Spawns system processes or shell commands",
        "check": lambda ioc, _: any(
            e["text"] in {"os.system", "os.popen", "os.execv", "os.execve",
                          "subprocess.Popen", "subprocess.call", "subprocess.run"}
            for e in ioc.suspicious_calls
        ),
    },
    {
        "tag": "NETWORK RECON",
        "desc": "Opens raw sockets or sends data over the network",
        "check": lambda ioc, _: any(
            e["text"] in {".connect()", ".sendall()", ".sendto()", ".bind()",
                          "socket.connect", "socket.sendto"}
            for e in ioc.suspicious_calls
        ),
    },
    {
        "tag": "REGISTRY MANIPULATION",
        "desc": "Reads or modifies Windows registry keys",
        "check": lambda ioc, _: any(
            e["text"].startswith("winreg.") for e in ioc.suspicious_calls
        ),
    },
    {
        "tag": "DYNAMIC EXECUTION",
        "desc": "Runs code generated or decoded at runtime via exec()/eval()",
        "check": lambda ioc, _: any(
            e["text"] in {"exec()", "eval()"} for e in ioc.suspicious_calls
        ),
    },
    {
        "tag": "EVASION",
        "desc": "Uses multiple obfuscation layers to hinder static analysis",
        "check": lambda _, counts: len(counts) >= 3,
    },
]


class BehaviorProfiler:
    def profile(
        self, ioc: IOCExtractor, technique_counts: dict[str, int]
    ) -> list[tuple[str, str]]:
        results = []
        for rule in _RULES:
            try:
                if rule["check"](ioc, technique_counts):
                    results.append((rule["tag"], rule["desc"]))
            except Exception:
                pass
        return results

    def print_report(self, behaviors: list[tuple[str, str]]) -> None:
        print("\n=== Behavior Profile ===")
        if not behaviors:
            print("  No specific threat behaviors detected.")
            return
        for tag, desc in behaviors:
            print(f"  [{tag:<22}] {desc}")
