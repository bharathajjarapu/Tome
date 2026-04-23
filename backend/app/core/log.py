"""Logging setup. Each entry point calls this once, before anything logs."""

import logging

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def setup(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=FORMAT)
