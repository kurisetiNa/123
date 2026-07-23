"""项目日志工具。

默认同时将日志输出到控制台和 ``logs/app.log``，日志文件按天轮转。
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional, Union

from utils.path_tool import get_abs_path


DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: str = "app",
    level: Union[int, str] = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """创建并返回一个日志记录器。

    :param name: 日志记录器名称
    :param level: 日志级别，例如 ``logging.INFO`` 或 ``"DEBUG"``
    :param log_file: 日志文件路径；相对路径以项目根目录为基准
    :return: 配置好的 ``logging.Logger``
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # 防止模块重复导入时反复添加 handler。
    if getattr(logger, "_project_logger_configured", False):
        return logger

    formatter = logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_path = log_file or get_abs_path(os.path.join("logs", "app.log"))
    if not os.path.isabs(file_path):
        file_path = get_abs_path(file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=file_path,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger._project_logger_configured = True  # type: ignore[attr-defined]
    return logger


# 大多数场景可直接从本模块导入使用。
logger = get_logger()

