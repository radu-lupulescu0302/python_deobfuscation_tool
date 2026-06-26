import unittest
from deobfuscator.static.transformers.imports import ImportsTransformer
from deobfuscator import stats
from tests.helpers import run_stmt, silent


class TestDunderImport(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(ImportsTransformer, src))

    def test_replaces_with_name(self):
        result = self._s("__import__('os').system('whoami')")
        self.assertIn("os.system('whoami')", result)

    def test_injects_import_statement(self):
        result = self._s("__import__('os').getcwd()")
        self.assertIn("import os", result)

    def test_does_not_duplicate_existing_import(self):
        result = self._s("import os\n__import__('os').getcwd()")
        self.assertEqual(result.count("import os"), 1)

    def test_multiple_modules(self):
        result = self._s("__import__('os')\n__import__('sys')")
        self.assertIn("import os", result)
        self.assertIn("import sys", result)


class TestAliasNormalisation(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def _s(self, src):
        return silent(lambda: run_stmt(ImportsTransformer, src))

    def test_alias_replaced_in_usage(self):
        result = self._s("import base64 as _b64\nx = _b64.b64decode(b'aA==')")
        self.assertIn("base64.b64decode", result)

    def test_alias_removed_from_import(self):
        result = self._s("import os as _os\n_os.system('x')")
        self.assertNotIn("as _os", result)

    def test_canonical_name_preserved(self):
        # 'import os' (no alias) should be untouched
        result = self._s("import os\nos.getcwd()")
        self.assertIn("import os", result)
        self.assertNotIn("as ", result)
