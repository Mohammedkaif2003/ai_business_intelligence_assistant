import argparse
import json
import sys
import traceback
import threading
import time
import pandas as pd
import numpy as np
import plotly.express as px

# Resource limits (best-effort): prefer POSIX `resource`, fallback to a psutil
# watchdog that terminates the process if memory grows too large.
MAX_MEMORY_MB = 300
MAX_CPU_SECONDS = 10


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-file", required=True)
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    out = {"status": "error", "error": "unknown"}
    try:
        # Load input dataframe (handle empty input CSVs gracefully)
        try:
            df = pd.read_csv(args.input_csv)
        except Exception as exc:
            try:
                # pandas raises EmptyDataError for empty files
                from pandas.errors import EmptyDataError

                # If it's specifically an EmptyDataError, default to empty DataFrame
                # Otherwise, fall back to an empty DataFrame as a best-effort safe default
                df = pd.read_csv(args.input_csv)
            except Exception as exc:
                df = pd.DataFrame()

        # Read user code
        with open(args.code_file, "r", encoding="utf-8") as f:
            code = f.read()

        # Provide safe globals
        safe_builtins = {
            "len": len,
            "min": min,
            "max": max,
            "sum": sum,
            "range": range,
            "enumerate": enumerate,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
        }

        safe_globals = {
            "pd": pd,
            "np": np,
            "px": px,
            "__builtins__": safe_builtins,
        }

        # Best-effort resource limits
        try:
            import resource

            # Address space (bytes)
            resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_MB * 1024 * 1024, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS + 1))
        except Exception as exc:
            # Fallback: use psutil to watch memory on platforms without `resource` (e.g., Windows)
            try:
                import psutil
                import os

                def _watch_memory(pid, limit_mb):
                    p = psutil.Process(pid)
                    while True:
                        try:
                            mem = p.memory_info().rss // (1024 * 1024)
                            if mem > limit_mb:
                                sys.stderr.write("Memory limit exceeded\n")
                                # aggressive exit
                                os._exit(1)
                        except Exception as exc:
                            try:
                                sys.stderr.write(f"Memory watcher error: {exc}\n")
                            except Exception as exc:
                                pass
                        time.sleep(0.1)

                watcher = threading.Thread(target=_watch_memory, args=(os.getpid(), MAX_MEMORY_MB), daemon=True)
                watcher.start()
            except Exception as exc:
                pass

        local_vars = {"df": df}

        # Execute code (in limited globals)
        compiled = compile(code, "<analysis>", "exec")
        exec(compiled, safe_globals, local_vars)

        result = local_vars.get("result", None)
        charts = local_vars.get("charts", [])

        # Serialize result into a predictable JSON structure
        if result is None:
            out = {"status": "ok", "result_type": "none", "result": None, "charts": []}
        elif isinstance(result, pd.DataFrame):
            csv_data = result.head(10000).to_csv(index=False)
            out = {"status": "ok", "result_type": "dataframe", "result_csv_data": csv_data, "charts": []}
        elif hasattr(result, "to_list") and not isinstance(result, (str, bytes)):
            try:
                val = list(result)
            except Exception as exc:
                try:
                    sys.stderr.write(f"failed_converting_result_to_list: {exc}\n")
                except Exception as exc:
                    pass
                val = str(result)
            out = {"status": "ok", "result_type": "list", "result": val, "charts": []}
        else:
            out = {"status": "ok", "result_type": "value", "result": str(result), "charts": []}

        # If charts are present, attempt to serialize plotly figures to JSON
        try:
            serialized_charts = []
            for c in charts or []:
                try:
                    import plotly.io as pio

                    if hasattr(c, "to_plotly_json") or hasattr(c, "to_dict"):
                        # pio.to_json returns a JSON string; prefer a parsed object
                        jstr = pio.to_json(c)
                        try:
                            serialized_charts.append(json.loads(jstr))
                        except Exception as exc:
                            try:
                                sys.stderr.write(f"failed_parsing_chart_json: {exc}\n")
                            except Exception as exc:
                                pass
                            serialized_charts.append(jstr)
                    else:
                        serialized_charts.append(str(c))
                except Exception as exc:
                    try:
                        sys.stderr.write(f"serialize_chart_failed: {exc}\n")
                    except Exception as exc:
                        pass
                    serialized_charts.append(str(c))
            if serialized_charts:
                out["charts"] = serialized_charts
        except Exception as exc:
            # best-effort: ignore chart serialization failures but log to stderr
            try:
                sys.stderr.write("Chart serialization failed\n")
            except Exception as exc:
                pass

    except Exception as exc:
        out = {"status": "error", "error": traceback.format_exc()}

    try:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, default=str)
    except Exception as exc:
        # If writing fails, log to stderr as last resort
        try:
            sys.stderr.write(json.dumps(out, ensure_ascii=False, default=str))
        except Exception as exc:
            pass


if __name__ == "__main__":
    main()
