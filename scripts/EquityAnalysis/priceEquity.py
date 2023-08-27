#
# Price Equity
# Script that applies fundamental techniques to calculate the fair price of an equity.
#

import pandas as pd
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
from nfpy.Financial import DDMModel
import nfpy.IO as IO
from nfpy.Tools import (Constants as Cn, Utilities as Ut)

__version__ = '0.5'
_TITLE_ = "<<< Price equity script >>>"

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    af = get_af_glob()
    cal = get_calendar_glob()
    inh = IO.InputHandler()

    end_date = inh.input("At which date perform the calculation? (default: today): ",
                         idesc='datetime', optional=True, default=today(mode='date'))
    years = inh.input("How long is the forecasting period (in years)?: ", idesc='float')

    # Calculate the starting date with a +.1 to ensure to have enough past data
    start_date = end_date - pd.Timedelta(days=Cn.DAYS_IN_1Y * (years + .1))
    cal.initialize(end_date, start_date)

    # Get equity
    q = "select * from Assets where type = 'Company'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print(f'\n\nAvailable companies:\n{tabulate(res, headers=f, showindex=True)}\n')
    uid_idx = inh.input(
        f'Give a company index: ',
        idesc='index', limits=(0, len(res) - 1)
    )
    uid = res[uid_idx][0]

    rrr = inh.input("Enter your required rate of return (decimal form): ", idesc='float')

    res = DDMModel(uid, stage1=(years, None, False), ke=rrr)

    print(f"\n----------------------------------\nInputs\n"
          f"\tActual price:\t\t\t\t\t{res['last_price']:.2f} {res['ccy']}\n"
          f"-------\nCalculations\n"
          f"\tDiscount rate:\t\t\t\t\t{res['ke']:.1%}\n"
          f"\tFair value zero-growth:\t\t\t{res['no_growth']['fv']:.2f}\n"
          f"\tReturn from actual zero-growth:\t{res['no_growth']['ret']:.1%}\n"
          f"-------\nResults w/ ROE method\n"
          f"\tFair value:\t\t\t\t\t\t{res['ROE_growth']['fv']:.2f}\n"
          f"\tReturn from actual:\t\t\t\t{res['ROE_growth']['ret']:.1%}\n"
          f"----------------------------------\n")

    Ut.print_ok('All done!')
