import unittest
from deobfuscator.static.transformers.xor_arithmetic import XorArithmeticTransformer
from deobfuscator import stats
from tests.helpers import run_stmt, silent


class TestXorLambda(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(XorArithmeticTransformer, src))

    def test_lambda_registered_and_decoded(self):
        src = (
            "cipher = lambda s: ''.join(chr(ord(c) ^ 7) for c in s)\n"
            "result = cipher('obkkh')"
        )
        result = self._s(src)
        self.assertIn("'hello'", result)

    def test_key_on_right(self):
        src = (
            "fn = lambda s: ''.join(chr(ord(c) ^ 42) for c in s)\n"
            "out = fn('BOFFE')"
        )
        result = self._s(src)
        self.assertIn("'hello'", result)

    def test_lambda_with_unknown_arg_not_decoded(self):
        # Argument is a variable, not a constant — should not be decoded statically
        src = (
            "fn = lambda s: ''.join(chr(ord(c) ^ 7) for c in s)\n"
            "out = fn(user_input)"
        )
        result = self._s(src)
        self.assertIn("fn(user_input)", result)


class TestInlineXorJoin(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(XorArithmeticTransformer, src))

    def test_generator_xor(self):
        # chr(ord(c) ^ 7) for c in 'obkkh'  →  'hello'
        src = "x = ''.join(chr(ord(c) ^ 7) for c in 'obkkh')"
        result = self._s(src)
        self.assertIn("'hello'", result)

    def test_key_commutative(self):
        # key ^ ord(c)  (key on left) should also be resolved
        src = "x = ''.join(chr(7 ^ ord(c)) for c in 'obkkh')"
        result = self._s(src)
        self.assertIn("'hello'", result)

    def test_non_constant_iter_not_decoded(self):
        src = "x = ''.join(chr(ord(c) ^ 7) for c in some_var)"
        result = self._s(src)
        self.assertNotIn("'hello'", result)
