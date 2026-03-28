"""
ログ管理モジュール
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
import config


class Logger:
    def __init__(self, name: str = "Process", log_file: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL))
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        import io
        console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'))
        console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        if log_file is None:
            log_file = config.LOG_DIR / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        else:
            log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.log_file = log_file
        self.logger.info(f"Logger initialized. Log file: {log_file}")

    def debug(self, msg: str): self.logger.debug(msg)
    def info(self, msg: str): self.logger.info(msg)
    def warning(self, msg: str): self.logger.warning(msg)
    def error(self, msg: str): self.logger.error(msg)
    def section(self, title: str):
        self.logger.info(f"\n{'='*60}\n  {title}\n{'='*60}")
    def step(self, step_num: int, description: str):
        self.logger.info(f"\n>>> Step {step_num}: {description}")


_global_logger = None

def get_logger(name: str = "Process") -> Logger:
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(name)
    return _global_logger
