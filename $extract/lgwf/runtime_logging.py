import logging
import pathlib
from typing import Any

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module


LOGGER_NAME = "lgwf.runtime"


def log_path_for(root: str | pathlib.Path = ".") -> pathlib.Path:
    return workspace_layout_module.runtime_log_path(root)


def configure_runtime_logger(root: str | pathlib.Path = ".") -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = log_path_for(root)
    file_ops_module.ensure_dir(log_path.parent)
    resolved_log_path = log_path.resolve()

    for handler in logger.handlers:
        if getattr(handler, "lgwf_log_path", None) == resolved_log_path:
            return logger

    handler = ClosingFileHandler(resolved_log_path)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(handler)
    return logger


class ClosingFileHandler(logging.Handler):
    def __init__(self, log_path: pathlib.Path) -> None:
        super().__init__()
        self.lgwf_log_path = log_path

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        with self.lgwf_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(message)
            log_file.write("\n")

    def __eq__(self, other: Any) -> bool:
        return self is other


