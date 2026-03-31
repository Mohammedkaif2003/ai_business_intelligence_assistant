import logging


LOGGER_NAME = "ai_business_intelligence_assistant"


def get_logger(name: str | None = None) -> logging.Logger:
    logger_name = LOGGER_NAME if not name else f"{LOGGER_NAME}.{name}"
    logger = logging.getLogger(logger_name)
    if not logging.getLogger(LOGGER_NAME).handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    return logger
