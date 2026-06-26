# Hybrid Python Malware Deobfuscator

A tool that takes obfuscated Python malware (code deliberately made hard to read) and outputs clean, readable Python source, along with IOC extraction and behavior profiling.

## Requirements

- Python **3.9+** (requires `ast.unparse`)
- No third-party dependencies — only the standard library (`ast`, `base64`, `zlib`, `binascii`, `codecs`, `re`, `marshal`, `threading`)
- **Optional:** `uncompyle6` — enables full source decompilation of `marshal.loads()` payloads in the static phase

## Usage

**Single file:**
```
python main.py <obfuscated_script.py> [-o output.py] [--static-only]
```

**Batch mode** (process every `.py` file in a directory):
```
python main.py <samples_dir/> [-o output_dir/] [--static-only]
```

Batch mode writes `clean_<filename>.py` into the output directory (default: `deobfuscated_batch/`) and prints an aggregated IOC report, technique summary, and behavior profile across all processed files.

| Flag | Description |
|---|---|
| `-o / --output` | Output file (single mode) or output directory (batch mode) |
| `--static-only` | Skip the dynamic analysis phase entirely |

---

## Project Structure

```
├── main.py                     # Entry point — argument parsing, single/batch dispatch
├── config.py                   # Global settings (MAX_STATIC_ITERATIONS=25, DYNAMIC_TIMEOUT=3s)
├── deobfuscator/
│   ├── pipeline.py             # HybridDeobfuscator — orchestrates static + dynamic phases
│   ├── metrics.py              # AST node counts, timing
│   ├── ioc_extractor.py        # IOC scanning (URLs, IPs, paths, registry keys, suspicious calls)
│   ├── behavior_profiler.py    # Behavior tagging (C2, persistence, dropper, …)
│   ├── stats.py                # Per-technique counters and confidence scores
│   ├── static/
│   │   ├── transformers/       # One file per AST transformer (see table below)
│   │   └── utils.py
│   └── dynamic/
│       ├── sandbox.py          # Sandboxed namespace execution with timeout
│       ├── hooks.py            # Exec/eval site finder and slice extractor
│       └── memory_dumper.py
├── tests/                      # 113 unit + integration tests
├── samples/                    # Synthetic obfuscated samples
└── real_samples/               # More realistic obfuscated samples
```

---

## How it works

It operates in two phases:

---

### Phase 1 — Static Analysis (no code is run)

The tool parses the file into an **AST** (Abstract Syntax Tree) and runs a series of transformers over it in a loop, until nothing changes anymore (up to 25 iterations). Each pass can unlock the next — e.g. folding `3+4` → `7` lets the XOR transformer decode a string, which lets constant propagation resolve `exec(x)`, which lets the execution transformer inline the payload.

| Transformer | What it finds | What it produces |
|---|---|---|
| **FoldingTransformer** | Constant math (`3 + 4`), string ops (`"a" * 5`), index/slice (`"abc"[1]`, `"dlrow olleh"[::-1]`), `getattr` calls | The computed result: `7`, `"aaaaa"`, `"b"`, `"hello world"` |
| **EncodingsTransformer** | `base64.b64decode(...)`, `zlib.decompress(...)`, `bytes.fromhex(...)`, `codecs.decode(...)`, `bytes([...]).decode()`, `''.join(map(chr, [...]))`, `marshal.loads(b'...')` | The decoded string/bytes constant, or decompiled source |
| **XorArithmeticTransformer** | XOR cipher lambdas: `cipher = lambda s: ''.join(chr(ord(c) ^ 7) for c in s)` followed by `cipher("encoded")` | The decrypted plaintext string |
| **ConstantPropagationTransformer** | Variables assigned a known constant earlier, e.g. `x = "hello"` then `exec(x)` | Replaces the variable reference with its literal value |
| **ImportsTransformer** | `__import__('os')` calls and import-alias obfuscation | Normalises to standard `import` statements |
| **ExecutionTransformer** | `exec("some code")` / `eval("some code")` where the argument is already a known string; `compile(src, …)` wrappers | Replaces the `exec(...)` call with the actual statements it would run |
| **DeadCodeTransformer** | Variables and imports no longer used after the above substitutions | Removes them entirely |

---

### Phase 2 — Dynamic Analysis (controlled code execution)

Some payloads can't be resolved statically. For those the tool:

1. Finds remaining `exec(variable)` or `eval(variable)` calls
2. Extracts the **minimal program slice** needed to compute that variable (only transitively required assignments, nothing else)
3. Runs that slice in a **sandboxed namespace** with a 3-second timeout
4. Captures the value the variable held at runtime
5. Replaces the `exec(...)` with the recovered inlined statements

The sandbox also handles `exec(marshal.loads(b'...'))` directly — it executes the code object, captures the resulting namespace and stdout, and reconstructs equivalent statements. If `uncompyle6` is installed, `marshal.loads` payloads are fully decompiled to source in the static phase instead.

---

## Supported obfuscation patterns

| Pattern | Example | Phase |
|---|---|---|
| Arithmetic folding | `3 * 4 + 1` | Static |
| String multiplication / concatenation | `"ha" * 3` | Static |
| String slicing / reversal | `"dlrow olleh"[::-1]` | Static |
| Character index | `"hello"[1]` | Static |
| getattr resolution | `getattr(os, 'system')` → `os.system` | Static |
| base64 (b64, b32, b16, b85, a85) | `base64.b64decode(b'...')` | Static |
| zlib decompression | `zlib.decompress(b'...')` | Static |
| Hex decoding | `bytes.fromhex("...")`, `binascii.unhexlify(...)` | Static |
| codecs decode | `codecs.decode(data, "rot_13")` | Static |
| Byte array decode | `bytes([112, 114, ...]).decode()` | Static |
| chr() array | `''.join(map(chr, [104, 101, ...]))` | Static |
| XOR cipher lambda | `cipher = lambda s: ''.join(chr(ord(c)^7) for c in s)` | Static |
| Inline XOR join | `''.join(chr(ord(c)^KEY) for c in "...")` | Static |
| marshal payload | `exec(marshal.loads(b'...'))` | Static (with decompiler) / Dynamic |
| compile() unwrapping | `code = compile(src, ...); exec(code)` → `exec(src)` → inlined | Static |
| `__import__` resolution | `__import__('os').system(...)` → `import os` + `os.system(...)` | Static |
| exec / eval inlining | `exec("print('hi')")` | Static |
| Dead code removal | Unused variables and imports | Static |
| Runtime-computed variables | `key = f(); exec(key)` | Dynamic |

---

## Output

The final AST is unparsed back to Python source and written to the output file (default: `deobfuscated.py`). Several reports are printed:

**Obfuscation Techniques Detected** — counts how many times each technique fired, sorted by frequency. Each line also shows a **confidence score** reflecting how deterministic that transformation is:

```
=== Obfuscation Techniques Detected ===
  dead code removal                   x14  [confidence: 75%]
  constant propagation                x7   [confidence: 80%]
  XOR cipher lambda                   x4   [confidence: 92%]
  chr() array                         x2   [confidence: 99%]
  base64.b64decode                    x1   [confidence: 99%]
  ...
```

| Technique | Confidence | Reason |
|---|---|---|
| Arithmetic / string folding | 99% | Pure computation — no ambiguity |
| base64 / zlib / hex / chr() | 99% | Fully reversible, standard library |
| XOR inline join | 95% | Deterministic once key and ciphertext are known |
| compile() unwrapping | 96% | Deterministic — just strips the wrapper |
| XOR lambda | 92% | Deterministic, but depends on correct lambda pattern match |
| exec()/eval() inlining | 88% | Requires argument to already be a resolved string |
| marshal decompilation | 88% | Decompiler output may differ stylistically from original |
| constant propagation | 80% | May miss aliased or conditionally-assigned variables |
| dead code removal | 75% | Heuristic — rare false positive possible on unused-looking live code |

**Obfuscation Complexity Score** — a single 0–100 score summarising how heavily protected the file was:

| Range | Label | Meaning |
|---|---|---|
| 0–20 | Low | Trivial single-technique obfuscation |
| 21–40 | Moderate | 2–3 techniques, few iterations |
| 41–60 | High | Multi-layer, several iterations |
| 61–80 | Very High | Many techniques + some dynamic analysis |
| 81–100 | Extreme | Maximum layering, dynamic execution required |

Computed from: number of unique techniques (×10, cap 40) + extra iterations beyond 1 (×8, cap 24) + dynamic sites resolved (×15, cap 15) + IOC category diversity (×5, cap 21).

**Deobfuscation Report**
- **Nodes reduced**: original AST node count → final count (a rough measure of how much obfuscation was removed)
- **Time taken**

**IOC Report** — scans the deobfuscated AST for threat indicators:

| Category | What is matched |
|---|---|
| `URL` | `http://`, `https://`, `ftp://` strings |
| `IPv4` | IPv4 address literals |
| `DOMAIN` | Bare hostnames with known TLDs (`.com`, `.net`, `.onion`, …) |
| `PATH_WIN` | Windows file paths (`C:\Windows\Temp\dropper.exe`) |
| `PATH_UNIX` | Unix paths under `/etc`, `/tmp`, `/var`, … |
| `REGISTRY` | Windows registry key paths (`HKCU\…`, `HKLM\…`) |
| `SUSPICIOUS` | Dangerous API calls (`os.system`, `subprocess.Popen`, `socket.connect`, `winreg.SetValueEx`, …) |

> The scanner runs before dead-code removal at every iteration, so IOCs inside variables that are later eliminated (unused C2 URLs, drop paths, registry keys) are still captured.

**Behavior Profile** — interprets the combined IOC and suspicious-call evidence to classify what the malware does:

| Tag | Triggered when |
|---|---|
| `C2 BEACONING` | URL/IP IOC + network call (`.connect()`, `requests.get`, …) |
| `PERSISTENCE` | Registry `Run` key IOC present |
| `FILE DROPPER` | Windows or Unix executable path IOC present |
| `PROCESS EXECUTION` | `os.system`, `subprocess.Popen`, `os.execv`, … |
| `NETWORK RECON` | Raw socket calls (`.connect()`, `.sendall()`, `.bind()`) |
| `REGISTRY MANIPULATION` | `winreg.SetValueEx` / `OpenKey` / `CreateKey` |
| `DYNAMIC EXECUTION` | Residual `exec()` / `eval()` in output |
| `EVASION` | 3 or more distinct obfuscation techniques detected |

Example output:
```
=== Behavior Profile ===
  [C2 BEACONING          ] Communicates with a remote server (URL/IP + network call)
  [PERSISTENCE           ] Survives reboots via registry Run key or startup path
  [FILE DROPPER          ] References or writes executable paths on disk
  [EVASION               ] Uses multiple obfuscation layers to hinder static analysis
```

---

## Tests

Run the full test suite from the project root:

```
python -m unittest discover -s tests -t .
```

113 tests covering every transformer individually (known input → expected output), the IOC extractor, and end-to-end pipeline tests against all sample files.

| Test file | What it covers |
|---|---|
| `tests/test_folding.py` | Arithmetic, string ops, slicing, getattr, dead-if elimination |
| `tests/test_encodings.py` | base64, zlib, hex, codecs, chr() array, bytes.decode |
| `tests/test_xor.py` | XOR lambda registration and decoding, inline join-XOR |
| `tests/test_propagation.py` | Constant substitution, reassignment invalidation |
| `tests/test_imports.py` | `__import__()` resolution, import alias normalisation |
| `tests/test_execution.py` | exec/eval inlining, compile() unwrapping |
| `tests/test_dead_code.py` | Dead import and variable removal |
| `tests/test_ioc.py` | IOC detection for all categories, deduplication |
| `tests/test_pipeline.py` | End-to-end deobfuscation of all sample files |

---

## Samples

Synthetic obfuscated scripts in `samples/` for testing and demonstration:

| File | Obfuscation techniques used |
|---|---|
| `sample1.py` | base64, zlib+base64, XOR lambda |
| `sample2.py` | base64, zlib, chr() array, XOR lambda, constant propagation |
| `sample3.py` | `map(chr, [...])`, XOR with runtime key, `bytes([...]).decode()` |
| `sample_compile.py` | base64 + `compile()` + `exec()` |
| `sample_dropper.py` | chr() array URL, hex-decoded path, zlib+base64 payload (file dropper) |
| `sample_ioc.py` | base64 payload with embedded C2 IP, file path, registry key, dangerous API calls |
| `sample_marshal.py` | `marshal.loads()` payload |
| `sample_multilayer.py` | base64 wrapping base64+zlib (nested multi-layer exec chain) |
| `sample_persistence.py` | base64 + XOR lambda, registry `Run` key persistence |
| `sample_rat_loader.py` | `__import__` obfuscation, base64, reverse-shell RAT |
| `sample_realistic.py` | chr() array, `__import__`, base64, XOR lambda, `compile()`+`exec()` |
| `sample_stealer.py` | XOR lambda, base64, Discord token stealer with webhook exfiltration |

More realistic samples (heavier obfuscation) are in `real_samples/`: `sample_dropper.py`, `sample_multilayer.py`, `sample_persistence.py`, `sample_rat_loader.py`, `sample_stealer.py`.
