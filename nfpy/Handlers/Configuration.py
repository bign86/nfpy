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

# Empty configuration file for on the fly generation
# TODO: make the file generation dynamic through the use of dictionaries
__CONTENT__ = """[DATABASE]
db_dir = {dbf}
db_name = {dbn}

[FOLDERS]
data_folder = {dataf}
backup_folder = {bakf}

[REPORTING]
zip_format = {zipf}
report_path = {rep_path}
report_arch_path = {rep_arch_path}
report_arch_dir = {rep_arch_dir}
report_retention = {rep_ret}

[IBAPI]
ib_interface = {ib_intfc}
ib_client_id = {ib_client}
ib_tws_port = {ib_port}

[OTHERS]
base_ccy = {bfx}
calendar_frequency = {calf}
"""

# Dictionary of parameters in the current configuration file
PARAMS_DICT__ = {'dbf': 'database folder', 'dbn': 'database name',
                 'dataf': 'data folder', 'bakf': 'backup folder',
                 'bfx': 'base currency', 'calf': 'default calendar frequency',
                 'ib_intfc': 'IBAPI interface', 'ib_client': 'IBAPI client ID',
                 'ib_port': 'IBAPI TWS port', 'zip_format': 'Archive format',
                 'rep_arch_path': 'Path to archive directory',
                 'rep_arch_dir': 'Archive directory',
                 'rep_ret': 'Report retention days',
                 'rep_path': 'Path to report directory'}


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
            return self._conf[k]
        except KeyError:
            raise KeyError(k, 'Key {} does not exists in configuration file'.format(k))

    def __setitem__(self, k: str, v: Any):
        self._conf[k] = v

    @property
    def conf(self) -> configparser.ConfigParser:
        return self._conf

    @property
    def db_path(self) -> str:
        return self._conf.get('DATABASE', 'db_path')

    @property
    def db_dir(self) -> str:
        return self._conf.get('DATABASE', 'db_dir')

    @property
    def backup_dir(self) -> str:
        return self._conf.get('FOLDERS', 'backup_folder')

    @property
    def data_dir(self) -> str:
        return self._conf.get('FOLDERS', 'data_folder')

    @property
    def base_ccy(self) -> str:
        return self._conf.get('OTHERS', 'base_ccy')

    @property
    def frequency(self) -> str:
        return self._conf.get('OTHERS', 'calendar_frequency')

    @property
    def ib_interface(self) -> str:
        return self._conf.get('IBAPI', 'ib_interface')

    @property
    def ib_client_id(self) -> int:
        return self._conf.getint('IBAPI', 'ib_client_id')

    @property
    def ib_tws_port(self) -> int:
        return self._conf.getint('IBAPI', 'ib_tws_port')

    @property
    def zip_format(self) -> str:
        return self._conf.get('REPORTING', 'zip_format')

    @property
    def report_path(self) -> str:
        return self._conf.get('REPORTING', 'report_path')

    @property
    def report_arch_path(self) -> str:
        return self._conf.get('REPORTING', 'report_arch_path')

    @property
    def report_arch_dir(self) -> str:
        return self._conf.get('REPORTING', 'report_arch_dir')

    @property
    def report_retention(self) -> int:
        return self._conf.getint('REPORTING', 'report_retention')

    def _get_conf_full_path(self) -> str:
        """ Return the full path of the nfpyConf.ini file by interrogating the
            current position of this very module.
            FIXME: The position must be standardized possibly in a configuration
                   folder somewhere in the user home.
        """
        # p = dirname(dirname(abspath(__file__)))
        return os.path.join(NFPY_ROOT_DIR, self.CONF_INI)

    def _parse(self):
        """ Parse the configuration file. """
        conf_path = self._get_conf_full_path()
        if not os.path.isfile(conf_path):
            raise ValueError('Supplied file does not exist! Please give a valid one.')

        config = configparser.ConfigParser()
        config.read(conf_path)

        db_path = os.path.join(config['DATABASE']['db_dir'], config['DATABASE']['db_name'])
        config['DATABASE']['db_path'] = db_path

        # fx = config['OTHERS']['base_ccy']
        # if fx not in BASE_CCY:
        #    raise ValueError('Base currency in nfpyConf.ini not valid')

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
    f.write(__CONTENT__.format(**parameters))
    f.close()
