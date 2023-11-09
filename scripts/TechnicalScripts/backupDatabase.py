#
# Backup Database
# Script to backup a database
#

import nfpy.DB as DB
from nfpy.Tools import Utilities as Ut

__version__ = '0.3'
_TITLE_ = "<<< Backup Database Script >>>"


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    DB.backup_db()

    Ut.print_ok('All done!')
