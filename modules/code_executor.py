import ast
import re
import builtins
import logging
import subprocess
import sys
import tempfile
import json
import os

import pandas as pd
import numpy as np
import plotly.express as px

logger = logging.getLogger(__name__)

MAX_CODE_LENGTH = 6000
MAX_AST_NODES = 900
MAX_INPUT_ROWS = 20000
MAX_RESULT_ROWS = 5000
SUBPROCESS_TIMEOUT = 6  # seconds

# Forbidden patterns are applied case-insensitively using regex for robustness.
FORBIDDEN_PATTERNS = [
    r"\bimport\b",
    r"\bos\b",
    r"\bsys\b",
    r"subprocess",
    r"\bopen\s*\(",
    r"__\w+__",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"write\s*\(",
    r"read\s*\(",
    r"shutil",
    r"pathlib",
    r"socket",
    r"\brequests\b",
    r"\bhttp\b",
]


class SafeCodeValidator(ast.NodeVisitor):
    BLOCKED_NAMES = {
        "__import__", "eval", "exec", "open", "compile", "globals", "locals",
        "vars", "input", "help", "dir", "getattr", "setattr", "delattr"
    }
    BLOCKED_ATTRS = {
        "__class__", "__dict__", "__bases__", "__subclasses__", "__globals__",
        "__code__", "__closure__", "__func__", "__self__", "__module__"
    }
    ALLOWED_NODES = (
        ast.Module, ast.Assign, ast.Expr, ast.Load, ast.Store, ast.Name, ast.Constant,
        ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Subscript, ast.Slice,
        ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call, ast.Attribute,
        ast.keyword, ast.IfExp, ast.ListComp, ast.DictComp, ast.SetComp,
        ast.GeneratorExp, ast.comprehension, ast.For, ast.If, ast.Pass,
        ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
        ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.Add,
        ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd
    )

    def generic_visit(self, node):
        if not isinstance(node, self.ALLOWED_NODES):
            raise ValueError(f"Unsupported code pattern: {type(node).__name__}")
        super().generic_visit(node)

    def visit_Name(self, node):
        if node.id in self.BLOCKED_NAMES or "__" in node.id:
            raise ValueError(f"Unsafe name detected: {node.id}")
        super().generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in self.BLOCKED_ATTRS or "__" in node.attr or node.attr.startswith("__"):
            raise ValueError(f"Unsafe attribute detected: {node.attr}")
        super().generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.BLOCKED_NAMES:
            raise ValueError(f"Unsafe call detected: {node.func.id}")
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"to_csv", "to_excel", "to_json", "to_pickle", "to_sql"}:
            raise ValueError(f"Unsafe output operation detected: {node.func.attr}")
        super().generic_visit(node)


def _run_subprocess_sandbox(code_str: str, df: pd.DataFrame):
    # Write code and input CSV to temp files, call sandbox subprocess, read JSON output
    sandbox_path = os.path.join(os.path.dirname(__file__), "_code_sandbox.py")
    if not os.path.exists(sandbox_path):
        raise RuntimeError("Sandbox script not found")

    with tempfile.TemporaryDirectory() as td:
        code_file = os.path.join(td, "code.py")
        input_csv = os.path.join(td, "input.csv")
        output_json = os.path.join(td, "output.json")

        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code_str)

        # Serialize input dataframe (limited rows)
        if isinstance(df, pd.DataFrame):
            df.head(MAX_INPUT_ROWS).to_csv(input_csv, index=False)
        else:
            # For non-DataFrame inputs, write an empty CSV
            pd.DataFrame().to_csv(input_csv, index=False)

        try:
            proc = subprocess.run(
                [sys.executable, sandbox_path, "--code-file", code_file, "--input-csv", input_csv, "--output-json", output_json],
                capture_output=True,
                timeout=SUBPROCESS_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "code execution timed out"}

        # If output JSON exists, load it
        if os.path.exists(output_json):
            try:
                with open(output_json, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.debug("failed_parsing_sandbox_output", exc_info=True)
                return {"status": "error", "error": "failed_parsing_sandbox_output"}

        # Fallback: include subprocess stderr for diagnostics
        stderr = proc.stderr.decode("utf-8", errors="ignore") if proc.stderr else ""
        stdout = proc.stdout.decode("utf-8", errors="ignore") if proc.stdout else ""
        return {"status": "error", "error": "no_output", "stdout": stdout, "stderr": stderr}


def execute_code(code, df):
    validation_result = validate_generated_code(code)
    if isinstance(validation_result, str):
        return validation_result

    # Use the original code string (not AST) for sandboxing
    code_str = code if isinstance(code, str) else ""

    try:
        sandbox_out = _run_subprocess_sandbox(code_str, df)
    except Exception as e:
        logger.exception("sandbox_launch_failed")
        return f"Code execution error: {str(e)}"

    if not isinstance(sandbox_out, dict):
        return "Code execution error: invalid sandbox response"

    if sandbox_out.get("status") != "ok":
        return f"Code execution error: {sandbox_out.get('error')}"

    rtype = sandbox_out.get("result_type")
    if rtype == "none":
        return "No result generated by the analysis code."
    if rtype == "dataframe":
        # Prefer inline CSV data (safer across temp dir cleanup), fallback to file path
        csv_data = sandbox_out.get("result_csv_data")
        try:
            if csv_data:
                from io import StringIO

                df_out = pd.read_csv(StringIO(csv_data))
            else:
                csv_path = sandbox_out.get("result_csv")
                df_out = pd.read_csv(csv_path) if csv_path and os.path.exists(csv_path) else pd.DataFrame()

            if len(df_out) > MAX_RESULT_ROWS:
                df_out = df_out.head(MAX_RESULT_ROWS)
            return df_out
        except Exception as exc:
            logger.debug("failed_reading_dataframe_result", exc_info=True)
            return "Code execution error: failed reading dataframe result"

    # list or value
    return sandbox_out.get("result")


def validate_generated_code(code):
    if not isinstance(code, str) or not code.strip():
        return "Unsafe code detected: empty code"

    if len(code) > MAX_CODE_LENGTH:
        return "Unsafe code detected: code too long"

    try:
        tree = ast.parse(code, mode="exec")
    except Exception as e:
        return f"Unsafe code detected: {str(e)}"

    node_count = sum(1 for _ in ast.walk(tree))
    if node_count > MAX_AST_NODES:
        return "Unsafe code detected: code too complex"

    # Stronger AST-based validation. We rely on explicit node checks instead
    # of fragile regex substring checks to reduce bypass surface area.
    class EnhancedValidator(ast.NodeVisitor):
        BLOCKED_NAMES = {
            "__import__", "eval", "exec", "open", "compile", "globals", "locals",
            "vars", "input", "help", "dir", "getattr", "setattr", "delattr"
        }
        BLOCKED_ATTRS = {
            "__class__", "__dict__", "__bases__", "__subclasses__", "__globals__",
            "__code__", "__closure__", "__func__", "__self__", "__module__"
        }
        # Modules and top-level names that should not be reachable from user code
        BLOCKED_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "pathlib", "requests", "http", "psutil"}
        # Attribute names that, when called, are dangerous (IO / process control)
        FORBIDDEN_CALL_ATTRS = {"to_csv", "to_excel", "to_json", "to_pickle", "to_sql", "popen", "Popen", "system", "run", "communicate", "connect", "send", "recv"}

        ALLOWED_NODES = (
            ast.Module, ast.Assign, ast.Expr, ast.Load, ast.Store, ast.Name, ast.Constant,
            ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Subscript, ast.Slice,
            ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call, ast.Attribute,
            ast.keyword, ast.IfExp, ast.ListComp, ast.DictComp, ast.SetComp,
            ast.GeneratorExp, ast.comprehension, ast.For, ast.If, ast.Pass, ast.Lambda,
            ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
            ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.Add,
            ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
            ast.USub, ast.UAdd
        )

        def generic_visit(self, node):
            if not isinstance(node, self.ALLOWED_NODES):
                raise ValueError(f"Unsupported code pattern: {type(node).__name__}")
            super().generic_visit(node)

        def visit_Import(self, node):
            raise ValueError("Import statements are not allowed")

        def visit_ImportFrom(self, node):
            raise ValueError("Import statements are not allowed")

        def visit_Name(self, node):
            name = node.id
            if name in self.BLOCKED_NAMES:
                raise ValueError(f"Unsafe name detected: {name}")
            # Reject dunder names like __import__ or __builtins__
            if name.startswith("__") or name.endswith("__"):
                raise ValueError(f"Unsafe dunder name detected: {name}")
            super().generic_visit(node)

        def visit_Attribute(self, node):
            attr = node.attr
            if attr in self.BLOCKED_ATTRS or attr.startswith("__"):
                raise ValueError(f"Unsafe attribute detected: {attr}")

            # If the attribute base is a blocked module (e.g., os.system)
            if isinstance(node.value, ast.Name) and node.value.id in self.BLOCKED_MODULES:
                raise ValueError(f"Access to dangerous module attribute: {node.value.id}.{attr}")

            super().generic_visit(node)

        def visit_Call(self, node):
            func = node.func
            # Direct calls to blocked names (eval, exec, getattr, etc.)
            if isinstance(func, ast.Name) and func.id in self.BLOCKED_NAMES:
                raise ValueError(f"Unsafe call detected: {func.id}")

            # Calls on attributes (e.g., df.to_csv(), os.system())
            if isinstance(func, ast.Attribute):
                if func.attr in self.FORBIDDEN_CALL_ATTRS:
                    raise ValueError(f"Unsafe call to attribute: {func.attr}")
                if isinstance(func.value, ast.Name) and func.value.id in self.BLOCKED_MODULES:
                    raise ValueError(f"Unsafe module call: {func.value.id}.{func.attr}")

            super().generic_visit(node)

    try:
        EnhancedValidator().visit(tree)
        return tree
    except Exception as e:
        return f"Unsafe code detected: {str(e)}"
