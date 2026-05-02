#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: **Add Desc**.
"""
import os
import time
import logging
from pathlib import Path

class CustomFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        # Define the maximum length of log level names
        self.level_lengths = {
            "INFO": 4,
            "WARNING": 7,
            "ERROR": 5,
            "DEBUG": 5,
            "CRITICAL": 8,
        }

    def format(self, record):
        # Calculate the padding required for the log level
        levelname = record.levelname
        max_length = max(self.level_lengths.values())
        padding = max_length - self.level_lengths.get(levelname, 0)

        # Add the padding to the log level
        record.levelname = " " * padding + f"[{levelname}]"

        # Shorten the file name to just the models name (without extension)
        record.filename = os.path.splitext(os.path.basename(record.filename))[0]

        # Only include location for DEBUG and ERROR logs
        if record.levelno in (logging.WARNING, logging.ERROR):
            record.location = f"[File:{record.filename}, Function:{record.funcName}, Line:{record.lineno}]"
        else:
            record.location = f"[{record.funcName}]"

        # Call the parent class's format method
        return super().format(record)

def get_logger(name: str, log_path: Path = None, file_level=logging.DEBUG, console_level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # master level — handlers filter from here

    # --- Sets the logging names ---
    log_path = log_path if log_path is not None else Path(Path(__file__).parent.parent.parent)
    log_path = log_path / "logs" / name / time.strftime("%Y_%m_%d") / f"{time.strftime("%H-%M-%S")}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # --- File handler: captures everything ---
    fh = logging.FileHandler(log_path)
    fh.setLevel(file_level)
    fh.setFormatter(CustomFormatter(
        fmt = "%(levelname)s %(asctime)s %(location)s %(message)s",
        datefmt = "%H:%M:%S"
    ))

    # --- Console handler: only shows INFO and above ---
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(CustomFormatter(
        fmt = "%(levelname)s %(asctime)s %(location)s %(message)s",
        datefmt = "%H:%M:%S"
    ))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger