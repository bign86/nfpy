#
# Price Equity
# Script that applies fundamental techniques to calculate the fair price of an equity
#

import pandas as pd
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Models import DividendDiscountModel
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
    f = list(qb.get_fields('Assets'))
    res = db.execute(q).fetchall()

    print('\n\nAvailable companies:')
    print(tabulate(res, headers=f, showindex=True))
    uid = inh.input("\nGive a company index: ", idesc='int')
    eq = res[uid][0]

    rrr = inh.input("Enter your required rate of return: ", idesc='float')
    if not rrr:
        raise ValueError('You must give a required rate of return.')

    res = DividendDiscountModel(eq, future_proj=years).result(d_rate=rrr)

    print('\n----------------------------------\nInputs')
    print('\tNum of dividends:\t\t\t{:.0f}'.format(res['div_num']))
    print('\tForecasting years:\t\t\t{:.0f}'.format(res['future_proj']))
    print('\tActual price:\t\t\t\t{:.2f}'.format(res['last_price']))
    print('-------\nCalculations')
    print('\tFrequency of dividends:\t\t{:.2f}'.format(res['div_freq']))
    print('\tPrice drift (yearly):\t\t{:.1f}%'.format(res['price_drift']*100))
    print('\tDividend drift (yearly):\t{:.1f}%'.format(res['div_drift']*100))
    print('-------\nResults')
    print('\tDiscount rate:\t\t\t\t{:.1f}%'.format(res['d_rate']*100))
    print('\tFair value zero-growth:\t\t{:.2f}'.format(res['fair_value_no_growth']))
    print('\tFair value:\t\t\t\t\t{:.2f}'.format(res['fair_value_with_growth']))

    print('All done!')
