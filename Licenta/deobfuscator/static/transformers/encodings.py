import ast
import base64
import binascii
import codecs
import zlib
from ..utils import is_constant
from .base import BaseTransformer
from ...stats import record


def _decompile_code_object(code_obj) -> str | None:
    """Try to decompile a code object to Python source using available tools."""
    try:
        import uncompyle6
        import io
        buf = io.StringIO()
        uncompyle6.code_deparse(code_obj, out=buf)
        return buf.getvalue().strip()
    except Exception:
        pass
    try:
        import decompile
        import io
        buf = io.StringIO()
        decompile.decompile(None, code_obj, out=buf)
        return buf.getvalue().strip()
    except Exception:
        pass
    return None


class EncodingsTransformer(BaseTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)

        # ── base64 variants ────────────────────────────────────────────────
        for fn in ("b64decode", "b32decode", "b16decode", "b85decode", "a85decode"):
            if self._is_attr_call(node, "base64", fn):
                if node.args and is_constant(node.args[0]):
                    try:
                        decoded = getattr(base64, fn)(node.args[0].value)
                        print(f"    [Encodings] base64.{fn} -> {len(decoded)} bytes")
                        record(f"base64.{fn}")
                        return ast.Constant(value=decoded)
                    except Exception as e:
                        print(f"    [Encodings] base64.{fn} failed: {e}")

        # ── zlib.decompress ────────────────────────────────────────────────
        if self._is_attr_call(node, "zlib", "decompress"):
            if node.args and is_constant(node.args[0]):
                data = node.args[0].value
                if isinstance(data, (bytes, bytearray)):
                    try:
                        decoded = zlib.decompress(data)
                        print(f"    [Encodings] zlib.decompress -> {len(decoded)} bytes: {decoded[:60]!r}")
                        record("zlib.decompress")
                        return ast.Constant(value=decoded)
                    except Exception as e:
                        print(f"    [Encodings] zlib failed: {e}")

        # ── bytes.fromhex("...") ───────────────────────────────────────────
        if self._is_attr_call(node, "bytes", "fromhex"):
            if node.args and is_constant(node.args[0]) and isinstance(node.args[0].value, str):
                try:
                    decoded = bytes.fromhex(node.args[0].value)
                    print(f"    [Encodings] bytes.fromhex -> {len(decoded)} bytes")
                    record("bytes.fromhex")
                    return ast.Constant(value=decoded)
                except Exception as e:
                    print(f"    [Encodings] bytes.fromhex failed: {e}")

        # ── binascii.unhexlify / a2b_hex ──────────────────────────────────
        for fn in ("unhexlify", "a2b_hex"):
            if self._is_attr_call(node, "binascii", fn):
                if node.args and is_constant(node.args[0]):
                    try:
                        decoded = binascii.unhexlify(node.args[0].value)
                        print(f"    [Encodings] binascii.{fn} -> {len(decoded)} bytes")
                        record(f"binascii.{fn}")
                        return ast.Constant(value=decoded)
                    except Exception as e:
                        print(f"    [Encodings] binascii.{fn} failed: {e}")

        # ── codecs.decode(data, encoding) ─────────────────────────────────
        if self._is_attr_call(node, "codecs", "decode"):
            if len(node.args) >= 2 and is_constant(node.args[0]) and is_constant(node.args[1]):
                data = node.args[0].value
                enc = node.args[1].value
                try:
                    decoded = codecs.decode(data, enc)
                    print(f"    [Encodings] codecs.decode(..., {enc!r}) -> {decoded!r}")
                    record(f"codecs.decode ({enc})")
                    return ast.Constant(value=decoded)
                except Exception as e:
                    print(f"    [Encodings] codecs.decode failed: {e}")

        # ── marshal.loads(bytes_const) ───────────────────────────────────────
        if self._is_attr_call(node, "marshal", "loads"):
            if node.args and is_constant(node.args[0]) and isinstance(node.args[0].value, bytes):
                try:
                    import marshal as _marshal
                    code_obj = _marshal.loads(node.args[0].value)
                    name = getattr(code_obj, "co_name", "?")
                    print(f"    [Marshal] loads -> code object '{name}'")
                    source = _decompile_code_object(code_obj)
                    if source:
                        print(f"    [Marshal] Decompiled to {len(source)} chars")
                        record("marshal.loads (decompiled)")
                        return ast.Constant(value=source)
                    else:
                        print(f"    [Marshal] No decompiler available — dynamic phase will handle exec()")
                except Exception as e:
                    print(f"    [Marshal] loads failed: {e}")

        # ── ''.join(map(chr, [int, ...])) ────────────────────────────────────
        if (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Constant)
                and node.func.value.value == ""
                and node.func.attr == "join"
                and node.args):
            arg = node.args[0]
            if (isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Name)
                    and arg.func.id == "map"
                    and len(arg.args) == 2
                    and isinstance(arg.args[0], ast.Name)
                    and arg.args[0].id == "chr"):
                seq = arg.args[1]
                if isinstance(seq, (ast.List, ast.Tuple)) and all(
                    isinstance(e, ast.Constant) and isinstance(e.value, int)
                    for e in seq.elts
                ):
                    try:
                        result = ''.join(chr(e.value) for e in seq.elts)
                        print(f"    [Encodings] ''.join(map(chr, [...])) -> {result!r}")
                        record("chr() array")
                        return ast.Constant(value=result)
                    except Exception as e:
                        print(f"    [Encodings] map(chr, ...) failed: {e}")

        # ── bytes([int, ...]).decode("utf-8" | ...) ───────────────────────
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "decode"
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Name)
                and node.func.value.func.id == "bytes"
                and node.func.value.args
                and isinstance(node.func.value.args[0], (ast.List, ast.Tuple))
                and all(isinstance(e, ast.Constant) and isinstance(e.value, int)
                        for e in node.func.value.args[0].elts)):
            enc = "utf-8"
            if node.args and is_constant(node.args[0]) and isinstance(node.args[0].value, str):
                enc = node.args[0].value
            try:
                data = bytes([e.value for e in node.func.value.args[0].elts])
                decoded = data.decode(enc, errors="ignore")
                print(f"    [Encodings] bytes([...]).decode({enc!r}) -> {decoded!r}")
                record("bytes([ints]).decode")
                return ast.Constant(value=decoded)
            except Exception as e:
                print(f"    [Encodings] bytes([...]).decode failed: {e}")

        # ── bytes_const.decode("utf-8" | "latin-1" | ...) ─────────────────
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "decode"
                and isinstance(node.func.value, ast.Constant)
                and isinstance(node.func.value.value, (bytes, bytearray))):
            enc = "utf-8"
            if node.args and is_constant(node.args[0]) and isinstance(node.args[0].value, str):
                enc = node.args[0].value
            try:
                decoded = node.func.value.value.decode(enc, errors="ignore")
                print(f"    [Encodings] bytes.decode({enc!r}) -> {decoded!r}")
                record("bytes.decode")
                return ast.Constant(value=decoded)
            except Exception as e:
                print(f"    [Encodings] bytes.decode failed: {e}")

        return node
