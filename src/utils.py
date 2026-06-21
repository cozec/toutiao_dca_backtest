"""Utility helpers: config loading, logging, and small shared functions."""

import logging
import os

import yaml

# Project root is one level above this file's directory (src/).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path=None):
    """Load the YAML configuration file.

    Args:
        path: Optional path to config.yaml. Defaults to <project_root>/config.yaml.

    Returns:
        dict: Parsed configuration.
    """
    if path is None:
        path = os.path.join(PROJECT_ROOT, "config.yaml")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def project_path(*parts):
    """Build an absolute path inside the project root."""
    return os.path.join(PROJECT_ROOT, *parts)


def ensure_dirs(*dirs):
    """Create each directory (and parents) if it does not already exist."""
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def setup_logging(log_file=None):
    """Configure root logging to both console and an optional file.

    Args:
        log_file: Optional path to a log file.

    Returns:
        logging.Logger: The configured root logger.
    """
    handlers = [logging.StreamHandler()]
    if log_file:
        ensure_dirs(os.path.dirname(log_file))
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("nasdaq_dca")
