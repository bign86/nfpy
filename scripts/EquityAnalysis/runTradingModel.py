#
# Run Trading Model
# Script to run a trading model on an equity
#

import numpy as np
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Trading.Strategies.BaseStrategy import (BaseStrategy, StrategyResult)

__version__ = '0.1'
_TITLE_ = "<<< Run trading model script >>>"


class StrategyToBeTested(BaseStrategy):

    def __init__(self, *args, _full_out: bool = False):
        super().__init__(_full_out)

    def _f(self, _dt: np.ndarray, _p: np.ndarray) -> tuple:
        # START CODE
        res = ()
        diz = {}
        # END CODE

        return StrategyResult(*res), diz


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    cal = get_calendar_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ",
                           idesc='datetime', optional=False)

    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp')
    cal.initialize(end_date, start_date)

    q = "select * from Assets where type = 'Equity'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print(f'\n\nAvailable equities:'
          f'{tabulate(res, headers=f, showindex=True)}',
          end='\n\n')
    uid = inh.input("\nGive an equity index: ", idesc='int')
    eq = af.get(res[uid][0])

    _args = inh.input("Insert parameters comma separated (default None): ",
                      default=[], is_list=True)

    p = eq.prices.values
    dt = cal.calendar.values
    try:
        strat = StrategyToBeTested(_args, True)
        signals = strat(dt, p)
    except (IndexError, TypeError) as ex:
        print(f'Signal generation failed for {eq.uid}\n{ex}')
    else:
        print(signals)

    print('All done!')
