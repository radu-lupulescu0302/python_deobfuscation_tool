import unittest
from deobfuscator.static.transformers.dead_code import DeadCodeTransformer
from deobfuscator import stats
from tests.helpers import run_stmt, silent


class TestDeadImports(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(DeadCodeTransformer, src))

    def test_unused_import_removed(self):
        result = self._s("import os\nx = 1")
        self.assertNotIn("import os", result)

    def test_used_import_kept(self):
        result = self._s("import os\nos.getcwd()")
        self.assertIn("import os", result)

    def test_unused_from_import_removed(self):
        result = self._s("from os import path\nx = 1")
        self.assertNotIn("import path", result)

    def test_used_from_import_kept(self):
        result = self._s("from os import path\npath.join('a', 'b')")
        self.assertIn("path", result)

    def test_aliased_import_used(self):
        result = self._s("import base64 as b64\nb64.b64decode(b'x')")
        self.assertIn("import base64", result)


class TestDeadAssignments(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(DeadCodeTransformer, src))

    def test_unused_variable_removed(self):
        result = self._s("x = 'unused'\nprint('hello')")
        self.assertNotIn("x = ", result)

    def test_used_variable_kept(self):
        result = self._s("x = 'used'\nprint(x)")
        self.assertIn("x = 'used'", result)

    def test_cascade_removal(self):
        # x depends on y; once x is removed, y becomes dead too (next pass)
        # Single pass: only x is removed
        result = self._s("y = 'helper'\nx = y\nprint('done')")
        self.assertNotIn("x = ", result)

    def test_tuple_target_not_removed(self):
        # Multi-target assignments are not touched (only simple Name targets)
        result = self._s("a, b = 1, 2\nprint('x')")
        self.assertIn("a, b", result)
