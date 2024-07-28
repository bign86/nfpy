#
# Add dividends to Yahoo
# Script to manually add dividends to the YahooEvents table. Dividends must be
# organized in the <ticker, date, dtype, value> format. No check is performed on
# the existence of the data, a simple DB.INSERT is performed.
#

import os
import pandas as pd

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.IO.Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Add dividends to Yahoo script >>>"
_DESC_ = """Manually add dividends to the YahooEvents table without replacement. Conflicting
data will generate an error."""

_TABLE = 'YahooDividends'
_COLS = ('ticker', 'date', 'value')


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
        df = pd.read_csv(f)
        df.columns = _COLS
        df['value'] = df['value'].astype(float)

        q = qb.insert(_TABLE)
        db.executemany(q, df.to_numpy(), commit=True)

    Ut.print_ok('All done!')
