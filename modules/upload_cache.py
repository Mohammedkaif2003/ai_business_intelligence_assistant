import hashlib


def compute_file_fingerprint(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def should_reuse_uploaded_dataframe(cached_df, cached_fingerprint: str | None, current_fingerprint: str) -> bool:
    return cached_df is not None and cached_fingerprint == current_fingerprint
