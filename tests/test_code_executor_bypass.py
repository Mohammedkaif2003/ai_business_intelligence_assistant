from modules.code_executor import validate_generated_code


def test_validate_blocks_dunder_imports():
    code = "result = __import__('os').system('echo hi')"
    res = validate_generated_code(code)
    assert isinstance(res, str)
    assert "Unsafe" in res or "Unsupported" in res


def test_validate_blocks_open_and_exec():
    for bad in ["open('x','w')", "eval('2+2')", "exec('a=1')"]:
        res = validate_generated_code(f"result = {bad}")
        assert isinstance(res, str)
        assert "Unsafe" in res or "Unsupported" in res
