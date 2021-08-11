#
# List reports
# Script to list available reports and their characteristics
#

import json
from tabulate import tabulate

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< List reports script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = Cal.get_calendar_glob()
    cal.initialize(Cal.today(), Cal.last_business())

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Choose a report to modify
    prk = tuple(qb.get_keys('Reports'))
    reports = db.execute(
        qb.selectall('Reports', fields=prk)
    ).fetchall()

    msg = f'Choose a report to show:\n' \
          f'{tabulate(reports, headers=prk, showindex=True)}\n' \
          f'Give an report index: '
    idx = inh.input(msg, idesc='int')

    # Fetch data
    data = db.execute(
        qb.select(
            'Reports',
            keys=prk
        ),
        reports[idx]
    ).fetchall()[0]

    msg = f'\nThe following are the details of the report:\n' \
          f'name:              {data[0]}\n' \
          f'report (py):       {data[1]}\n' \
          f'template (html):   {data[2]}.html\n' \
          f'active:            {"Yes" if bool(data[5]) else "No"}\n' \
          f'num. uids:         {len(data[3])}'
    print(msg, end='\n\n')

    msg = f'The following parameters have been defined:\n' \
          f'{json.dumps(data[4], indent=4, sort_keys=True)}'
    print(msg, end='\n\n')

    print('All done!')
