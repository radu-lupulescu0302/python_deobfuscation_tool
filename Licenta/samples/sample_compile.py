import base64

# Two-step: decode then compile then exec
src = base64.b64decode('aW1wb3J0IG9zCnJlc3VsdCA9IDQwICsgMgpwcmludCgiQW5zd2VyOiIsIHJlc3VsdCk=').decode()
code = compile(src, '<payload>', 'exec')
exec(code)
