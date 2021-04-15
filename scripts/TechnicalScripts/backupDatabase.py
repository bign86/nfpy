#
# Backup Database Script
# Script to backup a database
#

import nfpy.IO as IO

__version__ = '0.2'
_TITLE_ = "<<< Backup Database Script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    IO.backup_db()

    print('All done!')
