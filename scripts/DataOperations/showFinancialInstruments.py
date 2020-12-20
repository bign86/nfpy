#
# Show financial instruments
# Script to show all financial instruments known by the system
#

from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.2'
_TITLE_ = "<<< Show financial instruments script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    q = 'select * from Assets'

    msg = """Insert an asset class if you want to narrow down research: """
    choice = inh.input(msg, idesc='str')
    if choice:
        q = q + " where type = '{}'".format(choice)

    f = list(qb.get_fields('Assets'))
    res = db.execute(q).fetchall()

    print('\nResults:\n')
    print(tabulate(res, headers=f, showindex=True))

    print('\n\nfine')
