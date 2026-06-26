import unittest
from deobfuscator.static.transformers.propagation import ConstantPropagationTransformer
from deobfuscator import stats
from tests.helpers import run_stmt, silent


class TestConstantPropagation(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(ConstantPropagationTransformer, src))

    def test_simple_string(self):
        result = self._s("x = 'hello'\nprint(x)")
        self.assertIn("print('hello')", result)

    def test_simple_int(self):
        result = self._s("key = 42\nresult = key")
        self.assertIn("result = 42", result)

    def test_propagates_into_exec(self):
        result = self._s("payload = 'print(1)'\nexec(payload)")
        self.assertIn("exec('print(1)')", result)

    def test_reassignment_invalidates(self):
        # x is reassigned to a non-constant — should not propagate the original
        result = self._s("x = 'hello'\nx = some_func()\nprint(x)")
        self.assertNotIn("print('hello')", result)

    def test_does_not_propagate_non_constants(self):
        result = self._s("x = some_func()\nprint(x)")
        self.assertIn("print(x)", result)

    def test_multiple_uses(self):
        result = self._s("k = 7\na = k\nb = k")
        self.assertIn("a = 7", result)
        self.assertIn("b = 7", result)
