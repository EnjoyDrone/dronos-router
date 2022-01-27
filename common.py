#!/usr/bin/env python3

import pathlib
from pathlib import Path

# Script files
config_path  = str(pathlib.Path(__file__).parent.resolve()) + "/"

home_path = str(Path.home())
log_px4_path = home_path + "/drone/logs/px4/"
log_ulog_path  = home_path + "/drone/logs/ulog/"

# Time format
default_time_format = "%Y%m%d-%H%M%S" # Corresponds to yyyyMMdd-hhmmss

### Utilities ###

import os,csv

import json
import logging
import logging.config

def setup_logging(name):
    """
    Sets a logging configuration up from the json config file.

    Example of use::
        logger = cmn.setup_logging(Path(__file__).stem)
        logger.info("Logger started.")

    .. note::

        Environment variables will be used if defined:
          - LOG_CFG: The loggers config will be loaded from the given file.


    Parameters
    ----------
    name: str
        The name of the logging config to load (generally the basename of the
        script: __name__). Will be appended with ``_logging.json``.


    Returns
    -------
    logger: logging object
        A configured logger to use to log messages. Use ``logger.debug(str)``,
        ``logger.info(str)``, ``logger.warning(str)`` and ``logger.error(str)``.
    """
    # Create the logging directory
    os.makedirs(log_ulog_path, exist_ok=True)

    default_level=logging.INFO

    logger = logging.getLogger(name)

    # Load an environment variable to override current config
    override_env_key = 'LOG_CFG'
    override = os.getenv(override_env_key, None)

    if override:
        config_file = override
    else:
        config_file = os.path.join(config_path, "common_log.json")

    if os.path.exists(config_file):
        with open(config_file, 'rt') as f:
            config = json.load(f)
        # Edit the config to put log files in 'common_log_path'
        config["handlers"]["debug_file_handler"]["filename"] = os.path.join(
            log_ulog_path,
            config["handlers"]["debug_file_handler"].get(
                "filename",
                "aeros_ulog_debug.log"
            )
        )
        config["handlers"]["info_file_handler"]["filename"] = os.path.join(
            log_ulog_path,
            config["handlers"]["info_file_handler"].get(
                "filename",
                "aeros_ulog_info.log"
            )
        )
        config["handlers"]["error_file_handler"]["filename"] = os.path.join(
            log_ulog_path,
            config["handlers"]["error_file_handler"].get(
                "filename",
                "aeros_ulog_error.log"
            )
        )
        # Apply the config
        logging.config.dictConfig(config)
    else:
        print(f"The logging config file path '{config_file}' was not found.")
        logging.basicConfig(level=default_level)
    return logger
