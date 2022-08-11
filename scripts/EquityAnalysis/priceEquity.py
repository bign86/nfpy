#
# Price Equity
# Script that applies fundamental techniques to calculate the fair price of an equity
#

import pandas as pd
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
from nfpy.Financial.EquityValuation import DDM2s
import nfpy.IO as IO
from nfpy.Tools import Constants as Cn

__version__ = '0.3'
_TITLE_ = "<<< Price equity script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    af = get_af_glob()
    cal = get_calendar_glob()
    inh = IO.InputHandler()

    end_date = inh.input("At which date perform the calculation? (default: today): ",
                         idesc='datetime', optional=True, default=today(mode='datetime'))
    years = inh.input("How long is the forecasting period (in years)?: ", idesc='float')

    # Calculate the starting date with a +.1 to ensure to have enough past data
    start_date = end_date - pd.Timedelta(days=Cn.DAYS_IN_1Y * (years + .1))
    cal.initialize(end_date, start_date)

    # Get equity
    q = "select * from Assets where type = 'Company'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print(f'\n\nAvailable companies:\n'
          f'{tabulate(res, headers=f, showindex=True)}')
    uid = inh.input("\nGive a company index: ", idesc='int')
    eq = res[uid][0]

    rrr = inh.input("Enter your required rate of return: ", idesc='float')

    res = DDM2s(eq, future_proj=years).result(d_rate=rrr)

    print(f"\n----------------------------------\nInputs\n"
          f"\tNum of dividends:\t\t{res['div_num']:.0f}\n"
          f"\tForecasting years:\t\t{res['future_proj']:.0f}\n"
          f"\tActual price:\t\t\t{res['last_price']:.2f}\n"
          f"-------\nCalculations\n"
          f"\tFrequency of dividends:\t\t{res['div_freq']:.2f}\n"
          f"\tPrice drift (yearly):\t\t{res['price_drift'] * 100:.1f}%\n"
          f"\tDividend drift (yearly):\t{res['div_drift'] * 100:.1f}%\n"
          f"-------\nResults\n"
          f"\tDiscount rate:\t\t\t{res['d_rate'] * 100:.1f}%\n"
          f"\tFair value zero-growth:\t\t{res['fair_value_no_growth']:.2f}\n"
          f"\tFair value:\t\t\t{res['fair_value_with_growth']:.2f}")

    print('All done!')
