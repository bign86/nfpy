#
# Show financial instruments
# Script to show all financial instruments known by the system
#

from tabulate import tabulate

from nfpy.DB import (get_db_glob, get_qb_glob)
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.2'
_TITLE_ = "<<< Show financial instruments script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    inh = InputHandler()

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
