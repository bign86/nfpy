#
# Configuration
# Contains the configuration of the software
#

import configparser
import logging
import os
from os.path import (dirname, abspath)
from typing import Any

from nfpy import (NFPY_ROOT_DIR, __version__)

from .Singleton import Singleton

# Dictionary of parameters in the current configuration file
PARAMS_DICT__ = {
    'DATABASE': {
        'db_dir': (str, 'database folder'),
        'db_name': (str, 'database name'),
    },
    'FOLDERS': {
        'data_folder': (str, 'data folder'),
        'backup_folder': (str, 'backup folder'),
    },
    'REPORTING': {
        'zip_format': (str, 'Archive format'),
        'report_path': (str, 'Path to report directory'),
        'report_arch_path': (str, 'Path to archive directory'),
        'report_retention': (int, 'Report retention days'),
        'plot_long_win': (str, 'max'),
        'plot_short_win': (int, 120),
        'ewma_fast': (int, 21),
        'ewma_slow': (int, 120),
    },
    'BACKTESTING': {
        'backtest_path': (str, 'Path to backtest results directory'),
    },
    'IBAPI': {

        'ib_interface': (str, 'IBAPI interface'),
        'ib_client_id': (str, 'IBAPI client ID'),
        'ib_tws_port': (int, 'IBAPI TWS port'),
    },
    'LOGGING': {
        'log_level': (int, 'Log level'),
        'log_path': (str, 'Log file full path'),
    },
    'OTHERS': {
        'base_ccy': (str, 'Base currency'),
        'calendar_frequency': (str, 'Default calendar frequency'),
    }
}


class Configuration(metaclass=Singleton):
    """ Global configuration class """

    CONF_INI = 'nfpyConf.ini'

    def __init__(self):
        self._is_configured = False
        self._conf_path = None
        self._conf = None
        self._parse()

    def __bool__(self) -> bool:
        return self._is_configured

    __nonzero__ = __bool__

    def __getitem__(self, k: str) -> str:
        return getattr(self, k, None)

    def __setitem__(self, k: str, v: Any):
        setattr(self, k, v)

    def _get_conf_full_path(self) -> str:
        """ Return the full path of the nfpyConf.ini file by interrogating the
            current position of this very module.
            FIXME: The position must be standardized possibly in a configuration
                   folder somewhere in the user home.
        """
        return os.path.join(NFPY_ROOT_DIR, self.CONF_INI)

    def _parse(self) -> None:
        """ Parse the configuration file. """
        conf_path = self._get_conf_full_path()
        if not os.path.isfile(conf_path):
            raise ValueError('Supplied file does not exist! Give a valid one.')

        config = configparser.ConfigParser()
        config.read(conf_path)

        # Add full db_path property
        config['DATABASE']['db_path'] = os.path.join(
            config['DATABASE']['db_dir'],
            config['DATABASE']['db_name']
        )
        PARAMS_DICT__['DATABASE']['db_path'] = (str, '')

        for section in config.values():
            try:
                sect_p = PARAMS_DICT__[section.name]
            except KeyError:
                continue
            else:
                for k, v in section.items():
                    setattr(self, k, sect_p[k][0](v))

        self._conf_path = conf_path
        self._conf = config
        self._is_configured = True

    # def _start_logging(self) -> None:
    #     """ Starts the logging system. """
    #     log_path = os.path.join(self.log_path, 'nfpy.log')
    #     logging.basicConfig(
    #         filename=log_path,
    #         filemode='w',
    #         encoding='utf-8',
    #     )
    #     logger = logging.getLogger(__name__)
    #     logger.setLevel(self.log_level)
    #     logger.info('NFPY version {}'.format(__version__))


def get_conf_glob() -> Configuration:
    """ Returns the pointer to the global Configuration """
    return Configuration()


def create_new(parameters: dict):
    """ Creates a new empty configuration file in the standard position. """
    conf_path = os.path.join(
        dirname(dirname(abspath(__file__))),
        Configuration.CONF_INI
    )

    # remove existing file, NO BACKUP IS DONE!
    if os.path.isfile(conf_path):
        os.remove(conf_path)

    f = open(conf_path, "w")
    cp = configparser.ConfigParser()
    cp.read_dict(parameters)
    cp.write(f)
    f.close()
