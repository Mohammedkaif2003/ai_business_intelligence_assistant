from modules.code_executor import validate_generated_code


def test_blocks_dunder_builtins_access():
    code = "result = __builtins__['eval']('2+2')"
    res = validate_generated_code(code)
    assert isinstance(res, str)
    assert "Unsafe" in res or "Unsupported" in res


def test_blocks_subprocess_via_import():
    code = "result = __import__('subprocess').Popen(['echo','hi'])"
    res = validate_generated_code(code)
    assert isinstance(res, str)
    assert "Unsafe" in res or "Unsupported" in res


def test_blocks_object_dunder_getattribute():
    code = "result = object.__getattribute__(1, '__class__')"
    res = validate_generated_code(code)
    assert isinstance(res, str)
    assert "Unsafe" in res or "Unsupported" in res
