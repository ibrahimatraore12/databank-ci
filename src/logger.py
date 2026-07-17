# Journalisation structurée du projet - 4 flux distincts avec rotation
# Structured logging for the project - 4 separate flows with rotation

import logging
import os
from logging.handlers import RotatingFileHandler

import config

_LOGGERS = {}
VALID_FLOWS = ("pipeline", "ml", "api", "errors")


def get_logger(flow: str) -> logging.Logger:
    # Crée (ou réutilise) un logger avec rotation pour le flux demandé
    # Creates (or reuses) a rotating logger for the requested flow
    if flow in _LOGGERS:
        return _LOGGERS[flow]

    os.makedirs(config.LOGS_DIR, exist_ok=True)
    logger = logging.getLogger(f"databank_ci.{flow}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = RotatingFileHandler(
        os.path.join(config.LOGS_DIR, f"{flow}.log"),
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M"))
    logger.addHandler(handler)

    _LOGGERS[flow] = logger
    return logger


def log_event(flow: str, level: str, message: str, context: dict = None) -> None:
    # Écrit un évènement structuré dans le flux demandé, toujours dupliqué dans errors.log si niveau ERROR
    # Writes a structured event to the requested flow, always duplicated to errors.log if level is ERROR
    if flow not in VALID_FLOWS:
        flow = "pipeline"

    full_message = message if context is None else f"{message} | {context}"
    logger = get_logger(flow)
    getattr(logger, level.lower(), logger.info)(full_message)

    if level.upper() == "ERROR" and flow != "errors":
        get_logger("errors").error(full_message)
