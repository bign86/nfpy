#
# Add dividends to Yahoo
# Script to add manual dividends to Yahoo. Dividends must be organized in the
# <date, value> format.
#

import csv
import pandas as pd

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Add dividends to Yahoo script >>>"

_TABLE = 'YahooEvents'
_COLS = ('ticker', 'date', 'dtype', 'value')


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()
    cal = Cal.get_calendar_glob()
    cal.initialize(Cal.today(), '2010-01-01')

    file_name = inh.input('Insert file name: ')
    ticker = inh.input('Give ticker: ')

    f = open(file_name)
    data = csv.reader(f)
    df = pd.DataFrame(list(data))

    df.insert(0, 'ticker', ticker)
    df.insert(2, 'dtype', 6)
    df.columns = _COLS

    df['value'] = df['value'].apply(lambda v: float(v))

    q = qb.insert(_TABLE)
    db.executemany(q, df.values)

    print('All done!')
