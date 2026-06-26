#!/usr/bin/env python3
"""
Run this once to produce samples/sample3.py — a test for the *dynamic* phase.

Every pattern here survives the static phase unchanged because:

  Pattern 1 — map(chr, list)
    Static XorArithmeticTransformer only resolves ''.join(GeneratorExp/ListComp).
    map() is a Call node, not a comprehension, so it is ignored statically.

  Pattern 2 — sum()-derived XOR key
    The XOR lambda extractor looks for a Constant int on either side of BitXor.
    Here the key is Name('xor_key'), not a constant, so the lambda is never
    registered and the call is never resolved.

  Pattern 3 — bytes([list-of-ints]).decode()
    EncodingsTransformer handles bytes.fromhex(str) and b'...'.decode().
    bytes([int, int, ...]) is a constructor call with a List arg — not matched.

All three reach the dynamic phase, where the sandbox executes the minimal slice
that computes each variable, extracts the string, and inlines the payload.
"""
import os

# ── Payloads ──────────────────────────────────────────────────────────────────
MAP_PAYLOAD   = 'print("Hello from map(chr, ...)")'
SUM_KEY       = sum([3, 4])           # = 7; the *sample* computes this at runtime
SUM_PAYLOAD   = f'print("Hello, XOR key derived from sum()!")'
BYTES_PAYLOAD = 'print("Hello from bytes([...]).decode()")'

# ── Encode ────────────────────────────────────────────────────────────────────
map_ints   = list(MAP_PAYLOAD.encode())
sum_enc    = ''.join(chr(ord(c) ^ SUM_KEY) for c in SUM_PAYLOAD)
bytes_ints = list(BYTES_PAYLOAD.encode())

sample = f"""\
# sample3.py — dynamic-phase test
# All three exec() calls survive static analysis and are resolved at runtime.

# === Pattern 1: map(chr, list-of-ints) ===
# Static XorArithmeticTransformer only handles GeneratorExp/ListComp inside
# ''.join(...), not map().  The dynamic phase executes the slice and extracts
# payload1.
payload1 = ''.join(map(chr, {map_ints!r}))
exec(payload1)

# === Pattern 2: XOR key derived from sum() ===
# Static transformer cannot extract the XOR key because it is Name('xor_key'),
# not a Constant.  The sandbox executes the full three-line slice and returns
# the decoded string.
xor_key = sum([3, 4])
cipher = lambda s: ''.join(chr(ord(c) ^ xor_key) for c in s)
payload2 = cipher({sum_enc!r})
exec(payload2)

# === Pattern 3: bytes([list-of-ints]).decode() ===
# EncodingsTransformer handles bytes.fromhex() and b'...'.decode() but not
# the bytes([int,...]) constructor form.  The sandbox handles it trivially.
payload3 = bytes({bytes_ints!r}).decode()
exec(payload3)

print("=== sample3 finished ===")
"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample3.py')
with open(out, 'w', encoding='utf-8') as f:
    f.write(sample)
print(f"Written: {out}")
