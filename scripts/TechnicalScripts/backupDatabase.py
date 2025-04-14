#
# Backup Database
# Script to backup a database
#

import nfpy.DB as DB
import nfpy.IO.Utilities as Ut

__version__ = '0.3'
_TITLE_ = "<<< Backup Database Script >>>"


def main():
    Ut.print_header(_TITLE_, end='\n\n')
    DB.backup_db()
    Ut.print_ok('All done!')


if __name__ == '__main__':
    main()
