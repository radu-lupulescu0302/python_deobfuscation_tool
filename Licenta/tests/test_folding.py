import unittest
from deobfuscator.static.transformers.folding import FoldingTransformer
from deobfuscator import stats
from tests.helpers import run_expr, run_stmt, silent


class TestArithmeticFolding(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _e(self, src):
        return silent(lambda: run_expr(FoldingTransformer, src))

    def test_addition(self):
        self.assertEqual(self._e("3 + 4"), "7")

    def test_subtraction(self):
        self.assertEqual(self._e("10 - 3"), "7")

    def test_multiplication_ints(self):
        self.assertEqual(self._e("6 * 7"), "42")

    def test_multiplication_str_repeat(self):
        self.assertEqual(self._e('"ha" * 3'), "'hahaha'")

    def test_floor_div(self):
        self.assertEqual(self._e("10 // 3"), "3")

    def test_modulo(self):
        self.assertEqual(self._e("10 % 3"), "1")

    def test_power(self):
        self.assertEqual(self._e("2 ** 8"), "256")

    def test_bitxor(self):
        self.assertEqual(self._e("0xFF ^ 0x0F"), "240")

    def test_bitor(self):
        self.assertEqual(self._e("0b1010 | 0b0101"), "15")

    def test_bitand(self):
        self.assertEqual(self._e("0xFF & 0x0F"), "15")

    def test_lshift(self):
        self.assertEqual(self._e("1 << 4"), "16")

    def test_rshift(self):
        self.assertEqual(self._e("256 >> 4"), "16")

    def test_str_concat(self):
        self.assertEqual(self._e('"hel" + "lo"'), "'hello'")

    def test_unary_neg(self):
        self.assertEqual(self._e("-(-5)"), "5")

    def test_unary_not(self):
        self.assertEqual(self._e("not True"), "False")

    def test_invert(self):
        self.assertEqual(self._e("~0"), "-1")

    def test_nested(self):
        self.assertEqual(self._e("(2 + 3) * (4 - 1)"), "15")


class TestSubscriptFolding(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _e(self, src):
        return silent(lambda: run_expr(FoldingTransformer, src))

    def test_string_index(self):
        self.assertEqual(self._e('"hello"[1]'), "'e'")

    def test_string_negative_index(self):
        self.assertEqual(self._e('"hello"[-1]'), "'o'")

    def test_string_slice(self):
        self.assertEqual(self._e('"hello world"[0:5]'), "'hello'")

    def test_string_slice_from(self):
        self.assertEqual(self._e('"hello world"[6:]'), "'world'")

    def test_string_reverse(self):
        self.assertEqual(self._e('"dlrow olleh"[::-1]'), "'hello world'")

    def test_bytes_slice(self):
        self.assertEqual(self._e("b'hello'[1:-1]"), "b'ell'")


class TestGetattrFolding(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _e(self, src):
        return silent(lambda: run_expr(FoldingTransformer, src))

    def test_simple_getattr(self):
        self.assertEqual(self._e("getattr(os, 'system')"), "os.system")

    def test_getattr_chained_call(self):
        self.assertEqual(self._e("getattr(os, 'system')('whoami')"), "os.system('whoami')")

    def test_getattr_nested_attr(self):
        self.assertEqual(self._e("getattr(os.path, 'join')"), "os.path.join")

    def test_getattr_non_identifier_ignored(self):
        # 'not-an-id' is not a valid Python identifier — should not be folded
        result = self._e("getattr(x, 'not-an-id')")
        self.assertIn("getattr", result)


class TestDeadIfFolding(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(FoldingTransformer, src))

    def test_if_true_keeps_body(self):
        result = self._s("if True:\n    x = 1\nelse:\n    x = 2")
        self.assertIn("x = 1", result)
        self.assertNotIn("x = 2", result)

    def test_if_false_keeps_else(self):
        result = self._s("if False:\n    x = 1\nelse:\n    x = 2")
        self.assertNotIn("x = 1", result)
        self.assertIn("x = 2", result)
