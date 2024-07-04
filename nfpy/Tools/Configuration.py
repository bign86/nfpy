#
# Configuration
# Contains the configuration of the software
#

import configparser
from datetime import datetime
import numpy
import os
import shutil
from typing import Any

from nfpy import NFPY_ROOT_DIR, __version__

from .Exceptions import ConfigurationError
from .Logger import get_logger_glob
from .Singleton import Singleton


# New versions of numpy are printing an excessive amount of warning. This is to
# silence the divide-by-zero and the I-found-a-nan ones. As this is to be done
# as soon as possible BEFORE numpy gets used, configurations seems a good place.
numpy.seterr(divide='ignore', invalid='ignore')


_CONF_INI = 'nfpyConf.ini'
_OPSYS_HOME = '.nfpy'


class Configuration(metaclass=Singleton):
    """ Global configuration class """

    def __init__(self):
        self._is_configured = False
        self._conf_path = None
        self._conf = None
        self._parse()
        self._start_logging()

    def __bool__(self) -> bool:
        return self._is_configured

    __nonzero__ = __bool__

    def __getitem__(self, k: str) -> str:
        return getattr(self, k, None)

    def __setitem__(self, k: str, v: Any) -> None:
        setattr(self, k, v)

    @staticmethod
    def get_conf_paths() -> tuple[str, str]:
        """ Return the full path of the nfpyConf.ini file by interrogating the
            current position of this very module.
        """
        return (
            os.path.expanduser(os.path.join('~', _OPSYS_HOME)),
            NFPY_ROOT_DIR
        )

    def _parse(self) -> None:
        """ Parse the configuration file. """
        conf_path = None
        for path in self.get_conf_paths():
            full_path = os.path.join(path, _CONF_INI)
            if os.path.isfile(full_path):
                conf_path = full_path
                break
        if not conf_path:
            raise ValueError('No config file found! Aborting!')

        config = configparser.ConfigParser()
        config.read(conf_path)

        # Add full db_path property
        config['DATABASE']['db_path'] = os.path.join(
            config['DATABASE']['db_dir'],
            config['DATABASE']['db_name']
        )

        for section in config.values():
            for k, v in section.items():
                val = int(v) if v.isnumeric() else v
                setattr(self, k, val)

        self._conf_path = conf_path
        self._conf = config
        self._is_configured = True

    def _start_logging(self) -> None:
        """ Starts the logging system. """
        name = f'nfpy_{datetime.today().strftime("%Y%m%d")}.log'
        log_path = os.path.join(self.log_path, name)
        logger = get_logger_glob()
        logger.init(self.log_level, log_path)
        logger.info('NFPY version {}'.format(__version__))
        logger.info('DP Path {}'.format(self.db_path))


def get_conf_glob() -> Configuration:
    """ Returns the pointer to the global Configuration """
    return Configuration()


def create_new() -> None:
    """ Creates a new empty configuration file in the standard position. """
    conf_written = False

    dst, src = Configuration.get_conf_paths()
    if not os.path.exists(dst):
        try:
            os.makedirs(dst)
        except OSError as ex:
            print(f'Creation of directory {dst} failed')
            raise ex
        else:
            print(f'Successfully created directory {dst}')

    try:
        shutil.copyfile(
            os.path.join(src, _CONF_INI),
            os.path.join(dst, _CONF_INI)
        )
    except RuntimeError as ex:
        print(ex)
    else:
        conf_written = True

    if not conf_written:
        raise ConfigurationError('Could not write the configuration file!')
