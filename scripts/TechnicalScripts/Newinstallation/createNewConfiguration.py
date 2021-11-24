#
# Create Configuration file script
# Creates a new configuration file from scratch
#

from nfpy.Tools.Configuration import (PARAMS_DICT__, create_new)
from nfpy.Tools.Exceptions import ConfigurationError
from nfpy.Tools.Utilities import print_exc

__version__ = '0.2'
_TITLE_ = "<<< Configuration file creation script >>>"


def create_configuration():
    print('Insert the following parameters:')
    parameters = {}
    for section in PARAMS_DICT__.keys():
        sect_dict = {}
        for k, v in PARAMS_DICT__[section].items():
            p = input(f'{v[1]}: ').strip()
            sect_dict[k] = p if p else ''
        parameters[section] = sect_dict

    print('Creating new file...')
    try:
        create_new(parameters)
    except ConfigurationError as ex:
        print_exc(ex)
        exit()
    else:
        print("--- File Created! ---")


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')
    create_configuration()
