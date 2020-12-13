#
# Configuration
# Contains the configuration of the software
#

import configparser
import os
from os.path import dirname, abspath
from typing import Any

from nfpy import NFPY_ROOT_DIR
from nfpy.Tools.Singleton import Singleton

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
        'report_retention': (str, 'Report retention days')
    },
    'IBAPI': {

        'ib_interface': (str, 'IBAPI interface'),
        'ib_client_id': (str, 'IBAPI client ID'),
        'ib_tws_port': (int, 'IBAPI TWS port'),
    },
    'OTHERS': {
        'base_ccy': (str, 'base currency'),
        'calendar_frequency': (str, 'default calendar frequency')
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
        try:
            return getattr(self, k, None)
        except KeyError:
            raise KeyError(k, 'Key {} does not exists in configuration file'.format(k))

    def __setitem__(self, k: str, v: Any):
        setattr(self, k, v)

    def _get_conf_full_path(self) -> str:
        """ Return the full path of the nfpyConf.ini file by interrogating the
            current position of this very module.
            FIXME: The position must be standardized possibly in a configuration
                   folder somewhere in the user home.
        """
        return os.path.join(NFPY_ROOT_DIR, self.CONF_INI)

    def _parse(self):
        """ Parse the configuration file. """
        conf_path = self._get_conf_full_path()
        if not os.path.isfile(conf_path):
            raise ValueError('Supplied file does not exist! Give a valid one.')

        config = configparser.ConfigParser()
        config.read(conf_path)

        # Add full db_path property
        db_path = os.path.join(config['DATABASE']['db_dir'],
                               config['DATABASE']['db_name'])
        config['DATABASE']['db_path'] = db_path
        PARAMS_DICT__['DATABASE']['db_path'] = (str, '')

        for section in config.values():
            try:
                sect_p = PARAMS_DICT__[section.name]
            except KeyError as ex:
                pass
            else:
                for k, v in section.items():
                    setattr(self, k, sect_p[k][0](v))

        self._conf_path = conf_path
        self._conf = config
        self._is_configured = True


def get_conf_glob() -> Configuration:
    """ Returns the pointer to the global Configuration """
    return Configuration()


def create_new(parameters: dict):
    """ Creates a new empty configuration file in the standard position. """
    p = dirname(dirname(abspath(__file__)))
    conf_path = os.path.join(p, Configuration.CONF_INI)

    # remove existing file, NO BACKUP IS DONE!
    if os.path.isfile(conf_path):
        os.remove(conf_path)

    f = open(conf_path, "w")
    cp = configparser.ConfigParser()
    cp.read_dict(parameters)
    cp.write(f)
    f.close()
