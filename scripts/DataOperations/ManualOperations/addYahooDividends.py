#
# Add dividends to Yahoo
# Script to manually add dividends to the YahooEvents table. Dividends must be
# organized in the <ticker, date, dtype, value> format. No check is performed on
# the existence of the data, a simple DB.INSERT is performed.
#

import csv
import os
import pandas as pd

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Add dividends to Yahoo script >>>"
_DESC_ = """Manually add dividends to the YahooEvents table without replacement. Conflicting
data will generate an error."""

_TABLE = 'YahooEvents'
_COLS = ('ticker', 'date', 'dtype', 'value')


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()
    cal = Cal.get_calendar_glob()
    cal.initialize(Cal.today(), Cal.last_business())

    file_path = inh.input('Insert dividends file path: ')
    if not os.path.isfile(file_path):
        raise ValueError('Supplied file does not exist! Please give a valid one.')

    with open(file_path, 'r') as f:
        data = csv.reader(f)

    df = pd.DataFrame(list(data))
    df.columns = _COLS
    df['dtype'] = df['dtype'].apply(lambda v: int(v))
    df['value'] = df['value'].apply(lambda v: float(v))

    q = qb.insert(_TABLE)
    db.executemany(q, df.values, commit=True)

    Ut.print_ok('All done!')
