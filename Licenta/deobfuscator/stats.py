_counts: dict[str, int] = {}

# Confidence reflects how deterministic each transformation is (0-100).
# Exact names first; prefix fallback handled in get_confidence().
_CONFIDENCE: dict[str, int] = {
    # Constant folding / structural
    "constant folding":           99,
    "getattr() resolution":       85,
    "string slice":               99,
    # Encoding decoders (fully deterministic)
    "base64.b64decode":           99,
    "base64.b32decode":           99,
    "base64.b16decode":           99,
    "base64.b85decode":           99,
    "base64.a85decode":           99,
    "zlib.decompress":            99,
    "bytes.fromhex":              99,
    "binascii.unhexlify":         99,
    "binascii.hexlify":           99,
    "chr() array":                99,
    "bytes.decode":               98,
    # Marshal — decompiler output may differ from original source
    "marshal.loads (decompiled)": 88,
    # XOR — deterministic once key and ciphertext are known
    "XOR cipher lambda":          92,
    "XOR join (inline)":          95,
    # Data-flow analysis — may miss aliased or conditional assignments
    "constant propagation":       80,
    # Import normalisation
    "import alias obfuscation":   95,
    "__import__() call":          90,
    # Execution unwrapping
    "compile() wrapping":         96,
    "exec()/eval() inlining":     88,
    # Heuristic-based removal — rare false positives possible
    "dead code removal":          75,
}

# Prefix rules for dynamically-named techniques (e.g. "codecs.decode (rot_13)")
_CONFIDENCE_PREFIXES: list[tuple[str, int]] = [
    ("codecs.decode", 93),
    ("binascii.",     99),
    ("base64.",       99),
]


def record(technique: str) -> None:
    _counts[technique] = _counts.get(technique, 0) + 1


def get_counts() -> dict[str, int]:
    return dict(_counts)


def get_confidence(technique: str) -> int | None:
    if technique in _CONFIDENCE:
        return _CONFIDENCE[technique]
    for prefix, conf in _CONFIDENCE_PREFIXES:
        if technique.startswith(prefix):
            return conf
    return None


def reset() -> None:
    _counts.clear()
