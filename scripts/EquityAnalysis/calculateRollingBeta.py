#
# Calculate Rolling Beta
# Script to calculate the rolling Beta exposure of an instrument on an index
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.4'
_TITLE_ = "<<< Rolling Beta calculation script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    af = get_af_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ",
                           idesc='datetime', optional=False)
    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp')
    cal.initialize(end_date, start_date)

    f = list(qb.get_fields('Assets'))

    # Get equity
    eq_uid = inh.input("Give an equity uid (press Enter for a list): ",
                       optional=True)
    if not eq_uid:
        q = "select * from Assets where type = 'Equity'"
        res = db.execute(q).fetchall()

        msg = f'\n\nAvailable equities:\n' \
              f'{tabulate(res, headers=f, showindex=True)}\n' \
              f'Give an equity index: '
        idx = inh.input(msg, idesc='int')
        eq_uid = res[idx][0]
    eq = af.get(eq_uid)

    # Get indices list
    bmk_uid = inh.input("\nGive a list of indices uids (press Enter for a list): ",
                        optional=True, is_list=True)
    if not bmk_uid:
        q = "select * from Assets where type = 'Indices'"
        res = db.execute(q).fetchall()

        msg = f'\n\nAvailable indices:\n' \
              f'{tabulate(res, headers=f, showindex=True)}\n' \
              f'Default index: {eq.index}\n' \
              f'Give a list of indices comma separated (Default None): '
        idx = inh.input(msg, idesc='int', optional=True, is_list=True)
        bmk_uid = (
            res[i][0]
            for i in idx
        )

    # Rolling window size
    w = inh.input("\nChoose window size (Default 120): ", default=120,
                  idesc='int', optional=True)

    plt = IO.Plotter(
        1, 2,
        xl=('Date', 'Date'),
        yl=('Beta', 'Performance')
    ) \
        .lplot(1, eq.performance(), label=eq.uid, color='C0')

    for i, uid in enumerate(bmk_uid, start=1):
        bmk = af.get(uid)
        color = f'C{i}'
        dt, b, _ = eq.beta(bmk, w=w)
        plt.lplot(0, dt, b, label=bmk.uid, color=color)
        plt.lplot(1, bmk.performance(), label=bmk.uid, color=color)

    # min_date = int(cal.start.value * .95)
    # max_date = int(cal.end.value * 1.05)
    plt.set_limits(0, 'x', cal.start, cal.end) \
        .set_limits(1, 'x', cal.start, cal.end) \
        .plot() \
        .show()

    print('All done!')
