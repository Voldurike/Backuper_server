import os
from dotenv import load_dotenv
import pytz
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from html import escape
from logging import LogRecord


class SafeMessageFilter(logging.Filter):
    """Фильтр для автоматического экранирования сообщений"""
    def filter(self, record: LogRecord) -> bool:
        if hasattr(record, 'msg') and record.msg:
            # Экранирование спецсимволов и удаление переносов
            record.msg = escape(str(record.msg)).replace('\n', ' ')
        if hasattr(record, 'args') and record.args:
            # Экранирование аргументов сообщения
            record.args = tuple(
                escape(str(arg)).replace('\n', ' ') if isinstance(arg, str) else arg 
                for arg in record.args
            )
        return True


class TZFormatter(logging.Formatter):
    """Форматтер с поддержкой временных зон"""
    def __init__(self, tz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tz = tz

    def converter(self, timestamp):
        return datetime.fromtimestamp(timestamp, self.tz).astimezone(self.tz)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        return dt.strftime(datefmt) if datefmt else dt.isoformat()


class ServerLogger:
    def __init__(self):
        load_dotenv()
        os.makedirs('logs', exist_ok=True)
        
        self.log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
        self.log_rotation_days = int(os.getenv('LOG_ROTATION_DAYS', 7))
        self.log_encoding = os.getenv('LOG_ENCODING', 'utf-8')
        self.log_timezone = os.getenv('LOG_TIMEZONE', 'UTC')
        self.tz = self._get_timezone()
        
        self.logger = logging.getLogger('ServerLogger')
        self._setup_logger()

    def _get_timezone(self):
        try:
            return pytz.timezone(self.log_timezone)
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise ValueError(f"Unknown timezone: {self.log_timezone}") from e

    def _setup_logger(self):
        try:
            self.logger.setLevel(getattr(logging, self.log_level))
            
            # Общий фильтр для всех хендлеров
            safe_filter = SafeMessageFilter()
            
            # Форматтер
            formatter = TZFormatter(
                tz=self.tz,
                fmt='[%(asctime)s] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # Файловый хендлер
            file_handler = TimedRotatingFileHandler(
                filename='logs/server.log',
                when='midnight',
                backupCount=self.log_rotation_days,
                encoding=self.log_encoding
            )
            file_handler.suffix = '%Y-%m-%d.log'
            file_handler.addFilter(safe_filter)
            file_handler.setFormatter(formatter)

            # Консольный хендлер
            console_handler = logging.StreamHandler()
            console_handler.addFilter(safe_filter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        except Exception as e:
            self.logger.error(f"Logger initialization error: {str(e)}")
            raise

# Инициализация логгера
server_log = ServerLogger().logger
