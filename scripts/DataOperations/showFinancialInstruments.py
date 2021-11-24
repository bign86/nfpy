#
# Show financial instruments
# Script to show all financial instruments known by the system
#

from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.4'
_TITLE_ = "<<< Show financial instruments script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    uid = inh.input('Give a UID: ', idesc='str')
    ac = db.execute('select type from Assets where uid = ?', (uid,)).fetchone()
    while not ac:
        uid = inh.input('Not found. Please enter UID again: ', idesc='str')
        ac = db.execute('select type from Assets where uid = ?', (uid,)).fetchone()

    ac = ac[0]
    res = db.execute(f'select * from {ac} where uid = ?', (uid,)).fetchall()
    f = list(qb.get_fields(ac))
    print(f'\n{ac}\n{tabulate(res, headers=f)}', end='\n\n')

    print('All done!')
