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
    while not qb.exists_table(table):
        msg = 'Supplied table name does not exist! Please give a valid one: '
        table = inh.input(msg)

    print(qb.get_structure_string(table))

    print('All done!')
