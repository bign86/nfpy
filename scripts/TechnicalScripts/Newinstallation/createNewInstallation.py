#
# Create Database script
# Creates a new database from scratch
#

from nfpy.IO import Utilities as Ut
from nfpy.Tools.Configuration import create_new

from createNewDatabase import new_database

__version__ = '0.3'
_TITLE_ = "<<< New installation script >>>"


def install():
    print('--- Create new configuration ---')
    create_new()
    print('--- Create new database ---')
    new_database()


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    install()

    Ut.print_ok('All done!')
