#
# Print Portfolio Summary Script
# Print a summary of the content of a portfolio
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Constants as Cn

__version__ = '0.4'
_TITLE_ = "<<< Print portfolio summary script >>>"

_FMT_ = '%Y-%m-%d'


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    af = get_af_glob()
    inh = IO.InputHandler()

    cal = get_calendar_glob()
    end = today(mode='timestamp')
    start = cal.shift(end, -2*Cn.DAYS_IN_1Y, 'D')

    msg = "Give an start date (default {}): "
    start = inh.input(msg.format(start.strftime(_FMT_)), idesc='timestamp',
                      default=start, optional=True)

    cal.initialize(end=end, start=start)

    # Get equity
    q = "select * from Assets where type = 'Portfolio'"
    f = list(qb.get_fields('Assets'))
    res = db.execute(q).fetchall()

    print('\n\nAvailable portfolios:')
    print(tabulate(res, headers=f, showindex=True))
    idx = inh.input("\nGive a portfolio index: ", idesc='int')
    ptf_uid = res[idx][0]

    ptf = af.get(ptf_uid)
    f, d = ptf.summary()
    tot_value = ptf.total_value.at[cal.t0]

    print('\n *** Portfolio info ***\n------------------------\n')
    print('Uid:\t\t{}\nCurrency:\t{}\nDate:\t\t{}\nInception:\t{}\nTot. Value:\t{:.2f}'
          .format(ptf_uid, ptf.currency, ptf.date.strftime(_FMT_),
                  ptf.inception_date.strftime(_FMT_), tot_value))

    print('\n\n *** Summary of positions ***\n------------------------------\n')
    print(tabulate(d, headers=f), end='\n\n')

    print("All done!")
