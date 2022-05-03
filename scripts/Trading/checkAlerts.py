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

__version__ = '0.1'
_TITLE_ = '<<< Check manual alerts script >>>'

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    ae = Trd.AlertsEngine()
    db = DB.get_db_glob()
    cal = Cal.get_calendar_glob()
    inh = IO.InputHandler()

    end = Cal.today(mode='datetime')
    start = end - timedelta(days=90)
    cal.initialize(end=end, start=start)

    # Get input
    uids = inh.input('Give the list of uids to check. Leave empty to check all: ',
                     optional=True, is_list=True)

    # If no uid is given, take them all
    if uids is None:
        uids = [
            u[0] for u in
            db.execute('select distinct uid from Alerts')
              .fetchall()
        ]
        if not uids:
            print('No alerts found in the database.')
            exit()

    # Check for all breaches
    all_b = ae.fetch(
        uids,
        triggered=False,
    )
    all_b.sort(key=lambda f: f[0])

    data = []
    for uid, g in groupby(all_b, key=lambda f: f[0]):
        p = af.get(uid) \
              .last_price()[0]

        for a in g:
            cond = f'{"P >" if a.cond == "G" else "P <"} {a.value:.2f}'
            price = f'{p:.2f}'
            delta = f'{100.*a.value / p - 100.:.2f} %'
            data.append((a.uid, cond, price, delta))
    fields = ('uid', 'cond', 'price', 'delta')
    print(tabulate(data, fields), end='\n\n')

    print('All done!')
