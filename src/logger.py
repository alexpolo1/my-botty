import logging
import io
import os
import sys
import shutil
import threading
import traceback
import warnings
import zipfile
from logging.handlers import TimedRotatingFileHandler
from version import __version__
from colorama import Fore, Back, Style, init
import time

init()

class ArchiveRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that zips rotated files into log/archive/."""

    def doRollover(self):
        # Let the parent rotate the file (creates log.txt.1, etc.)
        super().doRollover()

        # Archive directory
        archive_dir = os.path.join("log", "archive")
        os.makedirs(archive_dir, exist_ok=True)

        # Zip all rotated backup files into log/archive/
        base_file = self.baseFilename  # e.g. "log/log.txt"
        for i in range(1, self.backupCount + 1):
            rotated = f"{base_file}.{i}"
            if os.path.exists(rotated):
                # Build zip name from the rotated file suffix
                # log.txt.1 -> log_20260528.zip (use modification time)
                mtime = os.path.getmtime(rotated)
                zip_name = f"log_{time.strftime('%Y%m%d_%H%M%S', time.localtime(mtime))}.zip"
                zip_path = os.path.join(archive_dir, zip_name)
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.write(rotated, os.path.basename(rotated))
                    os.remove(rotated)
                except Exception as e:
                    # If zipping fails, leave the rotated file in place
                    pass


class CustomFormatter(logging.Formatter):
    _format = f'[{__version__} %(asctime)s] %(levelname)-10s %(message)s'

    FORMATS = {
        logging.DEBUG:    Fore.WHITE          + _format + Fore.WHITE,
        logging.INFO:     Fore.LIGHTBLUE_EX   + _format + Fore.WHITE,
        logging.WARNING:  Fore.LIGHTYELLOW_EX + _format + Fore.WHITE,
        logging.ERROR:    Fore.LIGHTRED_EX    + _format + Fore.WHITE,
        logging.CRITICAL: Fore.RED            + _format + Fore.WHITE
    }


    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class Logger:
    """Manage logging"""
    os.makedirs("log", exist_ok=True)
    _logger_level = None
    _log_contents = io.StringIO()
    _current_log_file_path = "log/log.txt"
    _output = ""  # intercepted output from stdout and stderr
    string_handler = None
    file_handler = None
    console_handler = None
    logger = None

    @staticmethod
    def debug(data: str):
        if Logger.logger is None:
            Logger.init()
        Logger.logger.debug(data)

    @staticmethod
    def info(data: str):
        if Logger.logger is None:
            Logger.init()
        Logger.logger.info(data)

    @staticmethod
    def warning(data: str):
        if Logger.logger is None:
            Logger.init()
        Logger.logger.warning(data)

    @staticmethod
    def error(data: str):
        if Logger.logger is None:
            Logger.init()
        Logger.logger.error(data)

    @staticmethod
    def exception(data: str):
        if Logger.logger is None:
            Logger.init()
        Logger.logger.exception(data)

    @staticmethod
    def install_exception_hooks():
        def log_uncaught_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            Logger.error(
                "Uncaught exception:\n"
                + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            )

        def log_thread_exception(args):
            Logger.error(
                f"Uncaught exception in thread {args.thread.name}:\n"
                + "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            )

        sys.excepthook = log_uncaught_exception
        threading.excepthook = log_thread_exception

    @staticmethod
    def init(lvl = logging.DEBUG):
        """
        Setup logger for StringIO, console and file handler
        """
        Logger._logger_level = lvl

        if Logger.logger is not None:
            Logger.logger.warning("WARNING: logger was setup already, deleting all previously existing handlers")
            for hdlr in Logger.logger.handlers[:]:  # remove all old handlers
                Logger.logger.removeHandler(hdlr)

        # Create the logger
        Logger.logger = logging.getLogger("botty")
        for hdlr in Logger.logger.handlers:
            Logger.logger.removeHandler(hdlr)
        Logger.logger.setLevel(Logger._logger_level)
        Logger.logger.propagate = False

        # Setup the StringIO handler
        Logger._log_contents = io.StringIO()
        Logger.string_handler = logging.StreamHandler(Logger._log_contents)
        Logger.string_handler.setLevel(Logger._logger_level)

        # Setup the console handler
        Logger.console_handler = logging.StreamHandler(sys.stdout)
        Logger.console_handler.setLevel(Logger._logger_level)

        # Setup the file handler (rotating — daily, archives to log/archive/)
        Logger.file_handler = ArchiveRotatingFileHandler(
            Logger._current_log_file_path,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        Logger.file_handler.setLevel(Logger._logger_level)

        # Optionally add a formatter
        _format = CustomFormatter()
        Logger.string_handler.setFormatter(_format)
        Logger.console_handler.setFormatter(_format)
        Logger.file_handler.setFormatter(logging.Formatter(_format._format))

        # Add the handler to the logger
        Logger.logger.addHandler(Logger.string_handler)
        Logger.logger.addHandler(Logger.console_handler)
        Logger.logger.addHandler(Logger.file_handler)
        Logger.install_exception_hooks()

        # redirect stderr & stdout to logger, e.g. print("...")
        # would have to implement all the std func such as write() flush() etc.
        # sys.stderr = Logger
        # sys.stdout = Logger

    @staticmethod
    def remove_file_logger(delete_current_log: bool = False):
        """
        Remove the file logger to not write output to a log file
        """
        Logger.logger.removeHandler(Logger.file_handler)
        if delete_current_log and os.path.exists(Logger._current_log_file_path):
            try:
                os.remove(Logger._current_log_file_path)
            except PermissionError:
                warnings.warn(f"Could not remove {Logger._current_log_file_path}, permission denied")
