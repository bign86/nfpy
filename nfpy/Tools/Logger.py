import logging
from typing import Callable

from .Exceptions import LoggerError
from .Singleton import Singleton


__NAME__ = 'nfpy'


class Logger(metaclass=Singleton):

    def __init__(self):
        self._is_initialized = False
        self._l = None

    def __bool__(self) -> bool:
        return self._is_initialized

    def init(
            self,
            level: int,
            file: str
    ) -> None:
        logging.basicConfig(
            filename=file,
            filemode='a',
            encoding='utf-8',
        )
        logger = logging.getLogger(__NAME__)
        logger.setLevel(level)

        self._l = logger
        self._is_initialized = True

    def _check_init(f) -> Callable:
        def wrapper_check_init(self, *args, **kwargs):
            try:
                f(self, *args, **kwargs)
            except:
                raise LoggerError(f'Logger(): not initialized!')
        return wrapper_check_init

    @_check_init
    def log(self, *args, **kwargs) -> None:
        self._l.log(*args, **kwargs)

    @_check_init
    def info(self, *args, **kwargs) -> None:
        self._l.info(*args, **kwargs)

    @_check_init
    def debug(self, *args, **kwargs) -> None:
        self._l.debug(*args, **kwargs)

    @_check_init
    def warning(self, *args, **kwargs) -> None:
        self._l.warning(*args, **kwargs)

    @_check_init
    def error(self, *args, **kwargs) -> None:
        self._l.error(*args, **kwargs)


def get_logger_glob():
    return Logger()
