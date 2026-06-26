import ast
import base64
import zlib
import unittest
from deobfuscator.static.transformers.encodings import EncodingsTransformer
from deobfuscator import stats
from tests.helpers import run_expr, run_stmt, silent


class TestBase64(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _e(self, src):
        return silent(lambda: run_expr(EncodingsTransformer, src))

    def test_b64decode_bytes(self):
        self.assertEqual(self._e("base64.b64decode(b'aGVsbG8=')"), "b'hello'")

    def test_b64decode_str(self):
        self.assertEqual(self._e("base64.b64decode('aGVsbG8=')"), "b'hello'")

    def test_b32decode(self):
        encoded = base64.b32encode(b'hello').decode()
        result = self._e(f"base64.b32decode(b'{encoded}')")
        self.assertEqual(result, "b'hello'")

    def test_b16decode(self):
        encoded = base64.b16encode(b'hello').decode()
        result = self._e(f"base64.b16decode(b'{encoded}')")
        self.assertEqual(result, "b'hello'")


class TestZlib(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def test_decompress(self):
        compressed = zlib.compress(b'hello world')
        src = f"zlib.decompress({compressed!r})"
        result = silent(lambda: run_expr(EncodingsTransformer, src))
        self.assertEqual(result, "b'hello world'")


class TestHexDecoding(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _e(self, src):
        return silent(lambda: run_expr(EncodingsTransformer, src))

    def test_bytes_fromhex(self):
        self.assertEqual(self._e("bytes.fromhex('68656c6c6f')"), "b'hello'")

    def test_binascii_unhexlify(self):
        self.assertEqual(self._e("binascii.unhexlify('68656c6c6f')"), "b'hello'")


class TestCodecs(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def test_rot13(self):
        result = silent(lambda: run_expr(EncodingsTransformer, "codecs.decode('uryyb', 'rot_13')"))
        self.assertEqual(result, "'hello'")


class TestChrArray(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _e(self, src):
        return silent(lambda: run_expr(EncodingsTransformer, src))

    def test_join_map_chr_list(self):
        self.assertEqual(self._e("''.join(map(chr, [104, 101, 108, 108, 111]))"), "'hello'")

    def test_join_map_chr_tuple(self):
        self.assertEqual(self._e("''.join(map(chr, (72, 101, 108, 108, 111)))"), "'Hello'")

    def test_empty_list(self):
        self.assertEqual(self._e("''.join(map(chr, []))"), "''")


class TestBytesDecode(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _e(self, src):
        return silent(lambda: run_expr(EncodingsTransformer, src))

    def test_decode_utf8(self):
        self.assertEqual(self._e("b'hello'.decode('utf-8')"), "'hello'")

    def test_decode_default_utf8(self):
        self.assertEqual(self._e("b'hello'.decode()"), "'hello'")

    def test_decode_latin1(self):
        self.assertEqual(self._e("b'hello'.decode('latin-1')"), "'hello'")
