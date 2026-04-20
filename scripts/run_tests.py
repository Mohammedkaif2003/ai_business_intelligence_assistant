import pytest
import sys
import io
import os


def main():
    # Ensure project root is on sys.path so `modules` package imports work during pytest
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    buf = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf, buf
    try:
        # Run pytest and write junit xml
        ret = pytest.main(['-q', '--maxfail=1', '--junitxml=pytest_results.xml'])
    finally:
        sys.stdout, sys.stderr = old_out, old_err

    # Persist console output to a file for reliable retrieval
    with open('pytest_console.txt', 'w', encoding='utf-8') as f:
        f.write(f'EXIT_CODE: {ret}\n')
        f.write(buf.getvalue())

    print(f'WROTE pytest_console.txt and pytest_results.xml (exit={ret})')
    return ret


if __name__ == '__main__':
    code = main()
    sys.exit(code)
