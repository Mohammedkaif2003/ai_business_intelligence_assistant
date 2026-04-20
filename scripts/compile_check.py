import py_compile, traceback, sys
try:
    py_compile.compile('app.py', doraise=True)
    print('COMPILE_OK')
except Exception:
    traceback.print_exc()
    sys.exit(1)
