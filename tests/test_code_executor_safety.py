import pandas as pd

from modules.code_executor import execute_code, validate_generated_code, MAX_RESULT_ROWS


def test_validate_generated_code_blocks_unsafe_output_calls():
    code = "result = df.to_csv('x.csv')"
    result = validate_generated_code(code)
    assert isinstance(result, str)
    assert "Unsafe" in result


def test_validate_generated_code_blocks_oversized_code():
    code = "result = 1\n" + ("a=1\n" * 7000)
    result = validate_generated_code(code)
    assert isinstance(result, str)
    assert "too long" in result


def test_execute_code_truncates_large_dataframe_results():
    df = pd.DataFrame({"x": range(MAX_RESULT_ROWS + 200)})
    result = execute_code("result = df", df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == MAX_RESULT_ROWS
