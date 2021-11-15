#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import logging
import os
import re
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict

from absl import logging as absl_logging

from zenml.constants import ZENML_LOGGING_VERBOSITY
from zenml.enums import LoggingLevels

from zenml.constants import (  # isort: skip
    ABSL_LOGGING_VERBOSITY,
    APP_NAME,
)


class CustomFormatter(logging.Formatter):
    """Formats logs according to custom specifications."""

    grey: str = "\x1b[38;21m"
    pink: str = "\x1b[35m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33;21m"
    red: str = "\x1b[31;21m"
    bold_red: str = "\x1b[31;1m"
    purple: str = "\x1b[1;35m"
    reset: str = "\x1b[0m"

    format_template: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%("
        "filename)s:%(lineno)d)"
        if LoggingLevels[ZENML_LOGGING_VERBOSITY] == LoggingLevels.DEBUG
        else "%(message)s"
    )

    COLORS: Dict[LoggingLevels, str] = {
        LoggingLevels.DEBUG: grey,
        LoggingLevels.INFO: purple,
        LoggingLevels.WARN: yellow,
        LoggingLevels.ERROR: red,
        LoggingLevels.CRITICAL: bold_red,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Converts a log record to a (colored) string

        Args:
            record: LogRecord generated by the code.

        Returns:
            A string formatted according to specifications.
        """
        log_fmt = (
            self.COLORS[LoggingLevels[ZENML_LOGGING_VERBOSITY]]
            + self.format_template
            + self.reset
        )
        formatter = logging.Formatter(log_fmt)
        formatted_message = formatter.format(record)
        quoted_groups = re.findall("`([^`]*)`", formatted_message)
        for quoted in quoted_groups:
            formatted_message = formatted_message.replace(
                "`" + quoted + "`",
                "`"
                + self.reset
                + self.yellow
                + quoted
                + "`"
                + self.COLORS.get(LoggingLevels[ZENML_LOGGING_VERBOSITY]),
            )
        return formatted_message


LOG_FILE = f"{APP_NAME}_logs.log"


def get_logging_level() -> LoggingLevels:
    """Get logging level from the env variable."""
    verbosity = ZENML_LOGGING_VERBOSITY.upper()
    if verbosity not in LoggingLevels.__members__:
        raise KeyError(
            f"Verbosity must be one of {list(LoggingLevels.__members__.keys())}"
        )
    return LoggingLevels[verbosity]


def set_root_verbosity() -> None:
    """Set the root verbosity."""
    level = get_logging_level()
    if level != LoggingLevels.NOTSET:
        logging.basicConfig(level=level.value)
        get_logger(__name__).debug(
            f"Logging set to level: " f"{logging.getLevelName(level.value)}"
        )
    else:
        logging.disable(sys.maxsize)
        logging.getLogger().disabled = True
        get_logger(__name__).debug("Logging NOTSET")


def get_console_handler() -> Any:
    """Get console handler for logging."""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    return console_handler


def get_file_handler() -> Any:
    """Return a file handler for logging."""
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight")
    file_handler.setFormatter(CustomFormatter())
    return file_handler


def get_logger(logger_name: str) -> logging.Logger:
    """Main function to get logger name,.

    Args:
      logger_name: Name of logger to initialize.

    Returns:
        A logger object.

    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(get_logging_level().value)
    logger.addHandler(get_console_handler())

    # TODO [LOW]: Add a file handler for persistent handling
    # logger.addHandler(get_file_handler())
    # with this pattern, it's rarely necessary to propagate the error up to
    # parent
    logger.propagate = False
    return logger


def init_logging() -> None:
    """Initialize logging with default levels."""
    # Mute tensorflow cuda warnings
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    set_root_verbosity()

    # set absl logging
    absl_logging.set_verbosity(ABSL_LOGGING_VERBOSITY)
