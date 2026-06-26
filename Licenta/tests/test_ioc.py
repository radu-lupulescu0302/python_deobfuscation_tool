import ast
import unittest
from deobfuscator.ioc_extractor import IOCExtractor


def _scan(src: str) -> IOCExtractor:
    ioc = IOCExtractor()
    ioc.scan(ast.parse(src))
    return ioc


class TestIPv4Detection(unittest.TestCase):
    def test_detects_ipv4(self):
        ioc = _scan("c2 = '185.220.101.47'")
        self.assertIn("185.220.101.47", ioc.hits["IPv4"])

    def test_ignores_invalid_ip(self):
        ioc = _scan("x = '999.999.999.999'")
        self.assertEqual(ioc.hits["IPv4"], [])

    def test_ip_in_nested_string(self):
        ioc = _scan("url = 'http://185.220.101.47/gate'")
        self.assertIn("185.220.101.47", ioc.hits["IPv4"])


class TestURLDetection(unittest.TestCase):
    def test_http_url(self):
        ioc = _scan("u = 'http://evil.com/payload.bin'")
        self.assertTrue(any("evil.com" in v for v in ioc.hits["URL"]))

    def test_https_url(self):
        ioc = _scan("u = 'https://c2.attacker.net/beacon'")
        self.assertTrue(any("attacker.net" in v for v in ioc.hits["URL"]))

    def test_ftp_url(self):
        ioc = _scan("u = 'ftp://drop.server.ru/file.exe'")
        self.assertTrue(any("ftp://" in v for v in ioc.hits["URL"]))


class TestWindowsPathDetection(unittest.TestCase):
    def test_windows_path(self):
        ioc = _scan(r"p = 'C:\Windows\Temp\dropper.exe'")
        self.assertTrue(any("dropper.exe" in v for v in ioc.hits["PATH_WIN"]))

    def test_appdata_path(self):
        ioc = _scan("p = 'C:\\\\Users\\\\Public\\\\malware.exe'")
        self.assertTrue(len(ioc.hits["PATH_WIN"]) > 0)


class TestUnixPathDetection(unittest.TestCase):
    def test_tmp_path(self):
        ioc = _scan("p = '/tmp/.hidden-daemon'")
        self.assertTrue(any(".hidden-daemon" in v for v in ioc.hits["PATH_UNIX"]))

    def test_etc_path(self):
        ioc = _scan("p = '/etc/cron.d/backdoor'")
        self.assertTrue(len(ioc.hits["PATH_UNIX"]) > 0)


class TestRegistryDetection(unittest.TestCase):
    def test_hkcu_key(self):
        ioc = _scan(r"r = 'HKCU\Software\Microsoft\Windows\CurrentVersion\Run'")
        self.assertTrue(len(ioc.hits["REGISTRY"]) > 0)

    def test_hklm_key(self):
        ioc = _scan(r"r = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT'")
        self.assertTrue(len(ioc.hits["REGISTRY"]) > 0)


class TestSuspiciousCalls(unittest.TestCase):
    def test_os_system(self):
        ioc = _scan("import os\nos.system('whoami')")
        texts = [e["text"] for e in ioc.suspicious_calls]
        self.assertIn("os.system", texts)

    def test_subprocess_popen(self):
        ioc = _scan("import subprocess\nsubprocess.Popen(['cmd'])")
        texts = [e["text"] for e in ioc.suspicious_calls]
        self.assertIn("subprocess.Popen", texts)

    def test_socket_connect_via_method(self):
        # s.connect() — object is a variable, not the socket module directly
        ioc = _scan("import socket\ns = socket.socket()\ns.connect(('1.2.3.4', 4444))")
        texts = [e["text"] for e in ioc.suspicious_calls]
        self.assertIn(".connect()", texts)

    def test_no_false_positive_on_safe_call(self):
        ioc = _scan("print('hello')")
        self.assertEqual(ioc.suspicious_calls, [])

    def test_deduplication(self):
        # Same call scanned twice should not duplicate
        ioc = _scan("import os\nos.system('a')\nos.system('b')")
        texts = [e["text"] for e in ioc.suspicious_calls]
        self.assertEqual(texts.count("os.system"), 1)
