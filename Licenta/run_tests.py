import unittest
import sys


class VerboseResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.passed = 0

    def _short_name(self, test):
        cls  = test.__class__.__name__
        method = test._testMethodName
        return f"{cls}.{method}"

    def addSuccess(self, test):
        self.passed += 1
        print(f"  OK    {self._short_name(test)}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"  FAIL  {self._short_name(test)}")

    def addError(self, test, err):
        super().addError(test, err)
        print(f"  ERROR {self._short_name(test)}")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        print(f"  SKIP  {self._short_name(test)}  ({reason})")


loader = unittest.TestLoader()
suite  = loader.discover(start_dir="tests", top_level_dir=".")

result = VerboseResult()
suite.run(result)

total  = result.passed + len(result.failures) + len(result.errors)
passed = result.passed

if result.failures or result.errors:
    print("\n--- Failures & Errors ---")
    for test, tb in result.failures + result.errors:
        print(f"\n{test}")
        print(tb)

status = "OK" if not (result.failures or result.errors) else "FAILED"
print(f"\n{passed}/{total} tests passed  [{status}]")

if result.failures or result.errors:
    sys.exit(1)
