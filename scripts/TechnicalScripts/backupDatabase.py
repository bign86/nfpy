#
# Backup Database Script
# Script to backup a database
#

from nfpy.DB import backup_db

__version__ = '0.2'
_TITLE_ = "<<< Backup Database Script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    backup_db()

    print('All done!')
