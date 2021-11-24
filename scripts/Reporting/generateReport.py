#
# Create report
# Run the report engine on all automatic reports
#

from pandas import DateOffset
from tabulate import tabulate

from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Reporting import get_re_glob

__version__ = '0.1'
_TITLE_ = "<<< Report generation script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    end = today(mode='timestamp')
    start = end - DateOffset(months=120)
    cal.initialize(end, start)

    # Get reports
    rep_name = inh.input("Give report name (press Enter for a list): ",
                         optional=True)
    if not rep_name:
        fields = ('name', 'report', 'active')
        q = f"select {', '.join(fields)} from Reports"
        res = db.execute(q).fetchall()

        msg = f'\nAvailable reports:\n' \
              f'{tabulate(res, headers=fields, showindex=True)}\n' \
              f'Give a report index: '
        idx = inh.input(msg, idesc='int')
        while idx < 0 or idx > len(res):
            idx = inh.input('Not possible. Given another index: ', idesc='int')
        rep_name = res[idx][0]

    get_re_glob().run(names=(rep_name,))

    print('All done!')
