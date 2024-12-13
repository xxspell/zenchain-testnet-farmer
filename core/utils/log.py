import contextvars
import logging
import sys
import traceback

from loguru import logger

from core.settings import settings


class InterceptHandler(logging.Handler):
    def __init__(self, log_prefix_var):
        super().__init__()
        self.log_prefix_var = log_prefix_var

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name if record.levelname in logger._core.levels else record.levelno
            prefix_log_message = self.log_prefix_var.get()

            exc_info = record.exc_info
            if exc_info and exc_info[0] is not None:
                traceback_str = ''.join(traceback.format_exception(*exc_info))
                message = f"{record.getMessage()}\n{traceback_str}"
            else:
                message = record.getMessage()


            logger.bind(prefix_log_message=prefix_log_message).opt(depth=6, exception=record.exc_info).log(level, message)
        except Exception as e:
            print(f"Error in InterceptHandler: {e}")
            print(record.getMessage())


class XLogger:
    def __init__(self, logger):
        self.logger = logger
        self.logger.remove()

        self.logger.add(
            sys.stdout,
            level=settings.env.console_log,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                   "<level>{level: <8}</level> | <light-red>{extra[prefix_log_message]}</light-red>"
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            colorize=True,
            enqueue=True
        )
        self.logger.add(
            "application.log",
            level="DEBUG",
            format="{time} - {name}:{function}:{line} - {level} - {extra[prefix_log_message]}{message}",
            rotation="1 week",
            compression="zip",
            enqueue=True
        )

        self.log_prefix_var = contextvars.ContextVar("log_prefix_var", default="")
        logging.basicConfig(handlers=[InterceptHandler(self.log_prefix_var)], level=logging.DEBUG)

    def _bind(self):
        return self.logger.bind(prefix_log_message=self.log_prefix_var.get())

    def info(self, message):
        self.logger.opt(depth=1).bind(prefix_log_message=self.log_prefix_var.get()).info(message)

    def debug(self, message):
        self.logger.opt(depth=1).bind(prefix_log_message=self.log_prefix_var.get()).debug(message)

    def warning(self, message):
        self.logger.opt(depth=1).bind(prefix_log_message=self.log_prefix_var.get()).warning(message)

    def error(self, message):
        self.logger.opt(depth=1).bind(prefix_log_message=self.log_prefix_var.get()).error(message)

    def critical(self, message):
        self.logger.opt(depth=1).bind(prefix_log_message=self.log_prefix_var.get()).critical(message)

xlogger = XLogger(logger)