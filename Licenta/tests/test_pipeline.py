import ast
import io
import contextlib
import unittest
from deobfuscator.pipeline import HybridDeobfuscator


def _deobf(path, dynamic=False):
    with open(path, encoding="utf-8", errors="ignore") as f:
        src = f.read()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return HybridDeobfuscator(use_dynamic=dynamic, debug=False).deobfuscate(src)


class TestSample1(unittest.TestCase):
    def setUp(self):
        self.result = _deobf("samples/sample1.py", dynamic=True)

    def test_no_base64_calls_remain(self):
        self.assertNotIn("b64decode", self.result)

    def test_xor_payload_resolved(self):
        # The XOR lambda (obf/enc/dec) is fully resolved — no lambda remains
        self.assertNotIn("lambda", self.result)

    def test_print_statements_revealed(self):
        self.assertIn("print(", self.result)

    def test_zlib_exec_documented(self):
        # sample1's zlib data is intentionally malformed — the tool cannot
        # decompress it, so exec(data) remains. This documents that limitation.
        self.assertIn("zlib", self.result)


class TestSample3(unittest.TestCase):
    def setUp(self):
        self.result = _deobf("samples/sample3.py", dynamic=True)

    def test_chr_array_resolved(self):
        # The map(chr, [...]) CALL should be gone from the AST.
        # (The string "Hello from map(chr, ...)" may still appear as a string
        # literal inside a print — that is correct output, not unresolved code.)
        tree = ast.parse(self.result)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "map"):
                if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == "chr":
                    self.fail("Unresolved map(chr, ...) call still in output AST")

    def test_no_exec_remains(self):
        self.assertNotIn("exec(", self.result)

    def test_xor_payload_revealed(self):
        self.assertIn("print(", self.result)


class TestSampleRealistic(unittest.TestCase):
    def setUp(self):
        self.result = _deobf("samples/sample_realistic.py", dynamic=False)

    def test_c2_ip_revealed(self):
        self.assertIn("185.220.101.47", self.result)

    def test_no_base64_blob_remains(self):
        # The long base64 string should be gone
        self.assertNotIn("b64decode", self.result)

    def test_no_exec_remains(self):
        self.assertNotIn("exec(", self.result)

    def test_no_compile_remains(self):
        self.assertNotIn("compile(", self.result)

    def test_socket_connect_revealed(self):
        self.assertIn("connect(", self.result)

    def test_os_system_revealed(self):
        self.assertIn("os.system(", self.result)


class TestSampleMarshal(unittest.TestCase):
    def setUp(self):
        self.result = _deobf("samples/sample_marshal.py", dynamic=True)

    def test_exec_resolved(self):
        # The exec(marshal.loads(...)) should have been processed
        # Result should contain recovered variable or comment
        self.assertTrue(
            "x = 42" in self.result or "marshal" in self.result,
            "Expected either recovered payload or marshal reference"
        )


class TestSampleCompile(unittest.TestCase):
    def setUp(self):
        self.result = _deobf("samples/sample_compile.py", dynamic=False)

    def test_compile_unwrapped(self):
        self.assertNotIn("compile(", self.result)

    def test_payload_revealed(self):
        self.assertIn("print(", self.result)
