from modules.code_executor import validate_generated_code


def test_validate_blocks_getattr_and_dunder_imports():
    # Attempt common getattr-based bypasses
    code = "result = getattr(__import__('os'), 'system')('echo hi')"
    res = validate_generated_code(code)
    assert isinstance(res, str)
    assert "Unsafe" in res or "Unsupported" in res


def test_validate_blocks_dunder_attribute_access():
    # Accessing dunder attributes should be rejected
    code = "result = (lambda: 0).__class__"
    res = validate_generated_code(code)
    assert isinstance(res, str)
    assert "Unsafe" in res or "Unsupported" in res
