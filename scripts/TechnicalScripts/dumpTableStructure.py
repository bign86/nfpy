#
# Dump table structure script
#

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.2'
_TITLE_ = "<<< Dump table structure script >>>"


if __name__ == '__main__':

    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    table = inh.input("Give me a table to dump: ")
    t_exists = qb.exists_table(table)
    if not t_exists:
        raise ValueError('Supplied table name does not exist! Please give a valid one.')

    qb.print_structure(table)

    print('All done!')
