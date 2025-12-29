# app/logging_config.py
import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Convert string to logging level constant
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)  # Ensure log directory exists

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
            "level": LOG_LEVEL,
        },
        "file": {
            # Use TimedRotatingFileHandler for daily logs
            "()": TimedRotatingFileHandler,
            "filename": os.path.join(LOG_DIR, "app.log"),
            "formatter": "default",
            "level": LOG_LEVEL,
            "when": "D",          # Rotate every day
            "interval": 1,        # Every 1 day
            "backupCount": 7,     # Keep last 7 days
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
    logging.info("Logging is configured with daily rotation.")
