import logging
import sys
from logging import Logger
from pathlib import Path
from typing import Optional


def configure_logging(
    logger_name: Optional[str] = None,
    level: int = logging.INFO,
    log_to_file: bool = False,
    logfile_path: str = "logs/app.log",
) -> Logger:
    """
    Configures and returns a logger with:
      - Console (stdout) handler, INFO+ level
      - (Optional) Rotating file handler with DEBUG+ level

    :param logger_name: if None, configures the root logger; otherwise, a named logger
    :param level: logging level for console (default INFO)
    :param log_to_file: if True, also write logs to a rotating file
    :param logfile_path: path to the logfile (if log_to_file=True)
    :return: the configured Logger instance
    """

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.setLevel(level)

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    if log_to_file:
        from logging.handlers import RotatingFileHandler

        log_path = Path(logfile_path)
        if not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=logfile_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger
