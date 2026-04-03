from modules.upload_cache import compute_file_fingerprint, should_reuse_uploaded_dataframe


def test_compute_file_fingerprint_changes_with_content():
    first = compute_file_fingerprint(b"a,b\n1,2\n")
    second = compute_file_fingerprint(b"a,b\n1,3\n")
    assert first != second


def test_compute_file_fingerprint_stable_for_same_content():
    sample = b"x,y\n10,20\n"
    assert compute_file_fingerprint(sample) == compute_file_fingerprint(sample)


def test_should_reuse_uploaded_dataframe_true_on_matching_fingerprint():
    assert should_reuse_uploaded_dataframe(object(), "abc", "abc") is True


def test_should_reuse_uploaded_dataframe_false_on_mismatch_or_missing_df():
    assert should_reuse_uploaded_dataframe(object(), "abc", "xyz") is False
    assert should_reuse_uploaded_dataframe(None, "abc", "abc") is False
