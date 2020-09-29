#
# Dump table structure script
#

from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.1'
_TITLE_ = "<<< Dump table structure script >>>"

if __name__ == '__main__':

    qb = get_qb_glob()
    inh = InputHandler()

    table = inh.input("Give me a table to dump: ")
    t_exists = qb.exists_table(table)
    if not t_exists:
        raise ValueError('Supplied table name does not exist! Please give a valid one.')

    qb.print_structure(table)

    print('All done!')
