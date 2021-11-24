#
# Re-download series script
# Re-download from scratch a series and substitute the existing one. If the old
# dataset was longer, the data are dumped to file instead of modifying the DB.
#

from datetime import datetime
from enum import Enum
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
import nfpy.Tools.Utilities as Ut

__version__ = '0.1'
_TITLE_ = "<<< Re-download series script >>>"


class States(Enum):
    UNSET = 0
    PRINT = 1
    CONFR = 2
    BREAK = 3
    QUIT = 4


def _get_filters(_c, _d):
    field = inh.input('Column to filter for: ')
    while field not in fields:
        field = inh.input('Field doesn\'t exist. Try again: ')
    _c.append(field)
    search = inh.input('Search for: ')
    _d.append(search)


def _get_results(_c, _d):
    return db.execute(
        qb.select(_TABLE_, keys=_c),
        _d
    ).fetchall()


_TABLE_ = 'Downloads'

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    dwnf = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    fields = list(qb.get_fields(_TABLE_))
    print(f'Insert filters for the {_TABLE_} table with columns\n'
          f'{", ".join(fields)}')

    # Filter downloads
    state = States.UNSET
    columns, data = [], []
    result, item = None, None
    in_msg = 'Press "f" to filter, "q" to quit: '
    while state != States.BREAK:
        if state == States.PRINT:
            print(tabulate(result, headers=fields), end='\n\n')
            state = States.UNSET
        elif state == States.CONFR:
            print(tabulate(result, headers=fields), end='\n\n')
            if inh.input('Rebuild the series (Default False)?: ', idesc='bool',
                         default=False):
                item = result[0]
                state = States.BREAK
            else:
                state = States.QUIT
        elif state == States.QUIT:
            print('Quitting...')
            exit()
        else:
            do = inh.input(in_msg)
            if do == 'f':
                _get_filters(columns, data)
                result = _get_results(columns, data)
                if len(result) > 1:
                    state = States.PRINT
                elif len(result) == 1:
                    state = States.CONFR
                else:
                    state = States.QUIT
            elif do == 'q':
                state = States.QUIT

    # Download the series
    page = dwnf.create_page_obj(*item[:3])
    data = page.initialize(params={'currency': item[3], 'start': '1990-01-01'}) \
               .fetch() \
               .data

    # Download the previous series
    old_data = db.execute(
        page.select,
        (page.ticker,)
    ).fetchall()

    # Check whether the old data have been cut in the source
    new_start = datetime.strptime(
        data.iloc[0].at['date'],
        '%Y-%m-%d'
    )
    old_start = old_data[0][1]
    if new_start > old_start:
        msg = f'Old series start: {old_start.strftime("%Y-%m-%d")}\n' \
              f'New series start: {new_start.strftime("%Y-%m-%d")}\n' \
              f'The series will be dumped into a file.'
        Ut.print_wrn(RuntimeWarning(msg))
        page.dump()
    else:
        if inh.input('Backup the database? (default True): ',
                     idesc='bool', default=True):
            DB.backup_db()
        print('Saving to database...')
        page.save()

    print('All done!')
