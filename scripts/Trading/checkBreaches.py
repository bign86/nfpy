#
# Check breaches
# Script to check for triggered breaches for an instrument
#

from datetime import timedelta

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.Trading as Trd

__version__ = '0.1'
_TITLE_ = '<<< Check breaches script >>>'

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    cal = Cal.get_calendar_glob()
    inh = IO.InputHandler()

    # Get input
    uid = inh.input('Give the uid to check: ', checker='uid')
    days = inh.input('Time window for check in days (Default 10): ',
                     idesc='int', default=10)
    w_sr_fast = inh.input('Time window for fast WMA (Default 21): ',
                          idesc='int', default=21)
    w_sr_slow = inh.input('Time window for slow WMA (Default 120): ',
                          idesc='int', default=120)

    # Initialize calendar
    end = Cal.today(mode='datetime')
    start = end - timedelta(days=2 * w_sr_slow)
    cal.initialize(end=end, start=start)

    # Check for breaches
    be = Trd.BreachesEngine(w_check=days, w_sr_slow=w_sr_slow,
                            w_sr_fast=w_sr_fast)
    breach = be.raise_breaches(uid)

    # Print results
    if len(breach.breaches) > 0:
        msg = f'The following breaches have been found:\n'
        for b in breach.breaches:
            msg += f'  > {b:.2f} {breach.ccy}\n'
        print(msg)

    if len(breach.testing) > 0:
        msg = f'The following level have been tested:\n'
        for b in breach.testing:
            msg += f'  > {b:.2f} {breach.ccy}\n'
        print(msg)

    # Show plot
    pl = breach.plot().plot()
    pl.show()

    print('All done!')
