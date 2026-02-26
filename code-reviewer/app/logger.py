# 日志配置
import logging
import sys
from typing import Optional

from app.config import settings


def setup_logger(name: str = "app", level: Optional[str] = None) -> logging.Logger:
    """
    配置并返回logger实例

    Args:
        name: logger名称
        level: 日志级别，默认从环境变量读取

    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 设置日志级别
    log_level = level or getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 创建格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出（如果配置了日志目录）
    if settings.log_dir:
        import os
        os.makedirs(settings.log_dir, exist_ok=True)
        file_handler = logging.FileHandler(
            filename=f"{settings.log_dir}/{name}.log",
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 创建默认logger实例
logger = setup_logger()