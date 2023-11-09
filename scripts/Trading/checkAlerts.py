#
# Check manual alerts
# Script to check the distance between un-triggered manual alerts and the price
# of an instrument
#

from datetime import timedelta
from itertools import groupby
from tabulate import tabulate

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.Trading as Trd
from nfpy.Tools import Utilities as Ut

__version__ = '0.2'
_TITLE_ = '<<< Check manual alerts script >>>'

_LOOKBACK_W = 90
_FMT = (None, None, None, '.2f', '.2%')


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    af = get_af_glob()
    ae = Trd.AlertsEngine()
    db = DB.get_db_glob()
    cal = Cal.get_calendar_glob()
    inh = IO.InputHandler()

    end = Cal.today(mode='datetime')
    start = end - timedelta(days=_LOOKBACK_W)
    cal.initialize(end=end, start=start)

    # Get input
    uids = inh.input('Give the list of uids to check. Leave empty to check all: ',
                     optional=True, is_list=True)

    # If no uid is given, take them all
    if uids is None:
        uids = [
            u[0] for u in
            db.execute('select distinct [uid] from [Alerts]')
            .fetchall()
        ]
        if not uids:
            Ut.print_warn('No alerts found in the database.')
            exit()

    # Check for all breaches
    all_b = ae.fetch(uids, triggered=False)
    all_b.sort(key=lambda f: f[0])

    data = []
    for uid, g in groupby(all_b, key=lambda f: f[0]):
        eq = af.get(uid)
        p = eq.last_price()[0]

        for a in g:
            cond = f'{"P >" if a.cond == "G" else "P <"} {a.value:7.2f}'
            price = f'{p:.2f}'
            delta = a.value / p - 1.
            data.append((a.uid, eq.ticker, cond, price, delta))
    fields = ('uid', 'ticker', 'cond', 'price', 'delta')
    print(tabulate(data, fields, floatfmt=_FMT), end='\n\n')

    Ut.print_ok('All done!')
