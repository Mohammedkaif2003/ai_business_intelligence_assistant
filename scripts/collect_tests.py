import pytest
import io
import sys

if __name__ == '__main__':
    buf = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf, buf
    try:
        ret = pytest.main(['-q'])
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    out = buf.getvalue()
    with open('pytest_console_capture.txt', 'w', encoding='utf-8') as f:
        f.write(f'EXIT_CODE: {ret}\n')
        f.write(out)
    print('WROTE pytest_console_capture.txt')
