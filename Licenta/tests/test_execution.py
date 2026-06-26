import unittest
from deobfuscator.static.transformers.execution import ExecutionTransformer
from deobfuscator import stats
from tests.helpers import run_stmt, silent


class TestExecInlining(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(ExecutionTransformer, src))

    def test_exec_string_inlined(self):
        result = self._s("exec(\"print('hello')\")")
        self.assertIn("print('hello')", result)
        self.assertNotIn("exec(", result)

    def test_eval_string_inlined(self):
        result = self._s("eval('1 + 1')")
        self.assertIn("1 + 1", result)

    def test_exec_bytes_inlined(self):
        result = self._s("exec(b\"print('hi')\")")
        self.assertIn("print('hi')", result)

    def test_exec_invalid_python_kept_as_comment(self):
        result = self._s("exec('not valid !!!')")
        self.assertIn("#", result)

    def test_exec_variable_not_inlined(self):
        # Variable arg — ExecutionTransformer should leave it alone (dynamic phase handles it)
        result = self._s("exec(payload)")
        self.assertIn("exec(payload)", result)

    def test_multiline_payload(self):
        result = self._s("exec('x = 1\\nprint(x)')")
        self.assertIn("x = 1", result)
        self.assertIn("print(x)", result)


class TestCompileUnwrapping(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(ExecutionTransformer, src))

    def test_compile_string_unwrapped(self):
        result = self._s("code = compile(\"print('hi')\", '<s>', 'exec')")
        self.assertIn("\"print('hi')\"", result)
        self.assertNotIn("compile(", result)

    def test_compile_bytes_unwrapped(self):
        result = self._s("code = compile(b\"x = 1\", '<s>', 'exec')")
        self.assertIn("'x = 1'", result)

    def test_compile_variable_not_unwrapped(self):
        result = self._s("code = compile(src, '<s>', 'exec')")
        self.assertIn("compile(src", result)
