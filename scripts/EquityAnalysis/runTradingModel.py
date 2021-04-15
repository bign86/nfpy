#
# Run Trading Model
# Script to run a trading model on an equity
#

import numpy as np
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.IO as IO
from nfpy.Trading.BaseStrategy import (BaseStrategy, StrategyResult)

__version__ = '0.1'
_TITLE_ = "<<< Run trading model script >>>"


class StrategyToBeTested(BaseStrategy):

    def __init__(self, _p, _full_out: bool = False):
        super().__init__(_full_out)
        self._p = _p

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
    qb = IO.get_qb_glob()
    db = IO.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ",
                           idesc='datetime', optional=False)

    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp')
    cal.initialize(end_date, start_date)

    q = "select * from Assets where type = 'Equity'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print('\n\nAvailable equities:')
    print(tabulate(res, headers=f, showindex=True))
    uid = inh.input("\nGive an equity index: ", idesc='int')
    eq = af.get(res[uid][0])

    args = inh.input("Insert parameters comma separated (default None): ",
                     default=[], is_list=True)

    p = eq.prices.values
    dt = cal.calendar.values
    try:
        strat = StrategyToBeTested(args, True)
        signals = strat.f(dt, p)
    except (IndexError, TypeError) as ex:
        print('Signal generation failed for {}\n{}'.format(eq.uid, ex))
    else:
        print(signals)

    print('All done!')
