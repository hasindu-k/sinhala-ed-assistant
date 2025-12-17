# app/logging_config.py
import logging
import logging.config
import os
from dotenv import load_dotenv
load_dotenv()

# Convert string to logging level constant
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "default": {"format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"},
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": LOG_LEVEL,   # set explicitly
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "default",
            "level": LOG_LEVEL,   # set explicitly
            "encoding": "utf-8",
        },
    },

    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file"],
    },
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.info("Logging is configured.")