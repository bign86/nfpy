#
# Re-download series script
# Re-download from scratch a series and substitute the existing one. If the old
# dataset was longer, the data are dumped to file instead of modifying the DB.
#

from datetime import datetime
from enum import Enum
import pandas as pd
from requests import RequestException
from tabulate import tabulate

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
import nfpy.IO.Utilities as Ut
import nfpy.Tools.Exceptions as Ex

__version__ = '0.1'
_TITLE_ = "<<< Re-download series script >>>"


_TABLE_ = 'Downloads'
_FIELDS_ = list(DB.get_qb_glob().get_fields(_TABLE_))


class States(Enum):
    UNSET = 0
    PRINT = 1
    CONFR = 2
    BREAK = 3
    QUIT = 4


def _get_filters(_c, _d):
    field = inh.input(f'{", ".join(_FIELDS_)}\n  > column: ')
    while field not in _FIELDS_:
        Ut.print_warn(f'{Ut.Col.WARNING.value}  ! Field doesn\'t exist.{Ut.Col.ENDC.value}')
        field = inh.input(f'Try again: ')
    _c.append(field)
    search = inh.input(f'  > search for: ')
    _d.append(f'%{search}%')


def _get_results(_c, _d):
    return db.execute(
        qb.select(_TABLE_, partial_keys=_c),
        _d
    ).fetchall()


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    dwnf = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    print(f'Insert filters for the {_TABLE_} table with columns:\n'
          f'>\t{", ".join(_FIELDS_)}', end='\n\n')

    # Filter downloads
    state = States.UNSET
    columns, data = [], []
    result, item = None, None
    in_msg = 'Press "f" to filter, "q" to quit: '
    while state != States.BREAK:
        if state == States.PRINT:
            print(tabulate(result, headers=_FIELDS_), end='\n\n')
            state = States.UNSET
        elif state == States.CONFR:
            print(tabulate(result, headers=_FIELDS_), end='\n\n')
            if inh.input(
                'Rebuild the series? (default False): ',
                idesc='bool', default=False
            ):
                item = Dwn.NTDownload._make(result[0])
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
                    print('No records found. Try a different search')
                    state = States.UNSET
            elif do == 'q':
                state = States.QUIT

    # Download the series
    skipped, generator = Dwn.get_provider(item.provider)() \
        .get_download_generator((item,), True)
    _, page = list(generator)[0]
    today = Cal.today(mode='date')

    try:
        page.initialize(params={'start': '1990-01-01'}) \
            .fetch()
        _ = page.data

    except (Ex.MissingData, Ex.IsNoneError, RuntimeError,
            RequestException, ValueError, ConnectionError) as e:
        Ut.print_exc(e)
        Ut.print_exc(RuntimeError('The download has FAILED, quitting...'))

    except RuntimeWarning as w:
        Ut.print_wrn(w)
        data_upd = (today, item.provider, item.page, item.ticker)
        db.execute(dwnf.q_upd, data_upd, commit=True)

    else:
        print(f'Found {page.data.shape[0]} records.')

        # Download the previous series
        old_data = db.execute(
            page.select,
            (page.ticker,)
        ).fetchall()
        old_data = pd.DataFrame(
            data=old_data,
            columns=list(DB.get_qb_glob().get_fields(page.table)),
        )
        old_data.set_index(keys='date', drop=True, inplace=True)
        old_data.sort_index(inplace=True)

        # Check whether the old data have been cut in the source
        new_start = datetime.strptime(
            page.data.iloc[0].at['date'],
            '%Y-%m-%d'
        ).date()
        old_start = old_data.index[0]
        print(f'Old series start: {old_start.strftime("%Y-%m-%d")}\n'
              f'New series start: {new_start.strftime("%Y-%m-%d")}\n')

        # If the newer history is shorter than the one we already have on DB
        # we want to salvage the tail as it is not replaced.
        if new_start > old_start:
            Ut.print_wrn(RuntimeWarning(f'The series will be dumped into a file.'))

            # TODO: implement the overriding of the tail of the series
            page.dump()

        # If the newer history is equally long or longer than the one we already
        # have on DB, we just replace.
        else:
            # Backup the DB before writing
            if inh.input(
            'Backup the database? (default True): ',
                 idesc='bool', default=True
            ):
                print('Saving to database...')
                DB.backup_db()

            page.save()

    Ut.print_ok('All done!')
