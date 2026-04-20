import importlib, traceback

modules_to_check = [
    'modules.app_state',
    'modules.code_executor',
    'modules.data_loader',
]

for m in modules_to_check:
    try:
        importlib.import_module(m)
        import logging
        logging.getLogger(__name__).info("OK: %s", m)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("ERROR: %s -> %s: %s", m, type(e).__name__, e)
        traceback.print_exc()
