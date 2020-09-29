#
# Add Trade Script
# Script to add or remove trades from portfolios.
#

from tabulate import tabulate

from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Portfolio.PortfolioManager import PortfolioManager
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.1'
_TITLE_ = "<<< Add trade script >>>"

_COLS_ORDER = ['ptf_uid', 'date', 'pos_uid', 'buy_sell', 'currency',
               'quantity', 'price', 'costs', 'market']
_COLS_QUESTIONS = {
    'ptf_uid': ('Insert a portfolio uid: ', 'str'),
    'date': ('Insert date and time (%Y-%m-%d %H:%M:%S): ', 'timestamp'),
    'pos_uid': ('Insert position uid: ', 'str'),
    'buy_sell': ('Is buy position?: ', 'bool'),
    'currency': ('Insert currency uid: ', 'str'),
    'quantity': ('Insert quantity: ', 'float'),
    'price': ('Insert unitary price: ', 'float'),
    'costs': ('Insert trade costs (optional): ', 'float'),
    'market': ('Insert market of execution (optional): ', 'str')
}


def insert_trade_data():
    print('\n--- Insert trade data ---')

    data = list()
    for col in _COLS_ORDER:
        q, idesc = _COLS_QUESTIONS[col]
        in_data = inh.input(q, idesc=idesc)

        if col == 'buy_sell':
            in_data = 1 if in_data else 2
        elif col == 'date':
            in_data = in_data.to_pydatetime()

        data.append(in_data)

    # Insert trade
    pm.new_trade(*data)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    inh = InputHandler()

    # List available portfolios
    q_ptf = "select * from Assets where type = 'Portfolio'"
    fa = list(qb.get_fields('Assets'))
    res = db.execute(q_ptf).fetchall()

    print('\n\nAvailable portfolios:')
    print(tabulate(res, headers=fa, showindex=True))

    # User provides data
    pm = PortfolioManager()
    insert_trade_data()
    v = inh.input('\n -> Insert another trade?: ', idesc='bool')
    while v:
        insert_trade_data()
        v = inh.input('\n -> Insert another trade?: ', idesc='bool')

    print("All done!")
