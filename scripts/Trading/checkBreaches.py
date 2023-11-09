#
# Check breaches
# Script to check for triggered breaches for an instrument
#

from datetime import timedelta

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut
import nfpy.Trading as Trd

__version__ = '0.2'
_TITLE_ = '<<< Check breaches script >>>'


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    cal = Cal.get_calendar_glob()
    inh = IO.InputHandler()

    # Get input
    uid = inh.input('Give the uid to check: ', checker='uid')
    days = inh.input('Time window for check in days (default 10): ',
                     idesc='int', default=10)
    tol = inh.input('Percentage tolerance for the grouping (default 0.2): ',
                    idesc='float', default=.2)

    mode, w, thrs = None, None, None
    is_valid_mode = False
    while not is_valid_mode:
        mode = inh.input("Mode (\'smooth\' or \'pivot\') (default smooth): ",
                         idesc='str', default='smooth')
        if mode == 'smooth':
            w = inh.input('List of window length for the smoothing: ',
                          idesc='int', is_list=True, optional=False)
            is_valid_mode = True
        elif mode == 'pivot':
            thrs = inh.input('Return threshold to determine the pivot (default 0.2): ',
                             idesc='float', default=.2, optional=True)
            is_valid_mode = True

    # Initialize calendar
    if w is None:
        time_delta = days
    else:
        time_delta = max((*w, days))

    end = Cal.today(mode='datetime')
    start = end - timedelta(days=2 * time_delta)
    cal.initialize(end=end, start=start)

    # Check for breaches
    breaches = Trd.SRBreach(uid, days, tol=tol, mode=mode, w=w, thrs=thrs)

    # Print results
    if len(breaches) > 0:
        msg = f'The following breaches have been found:\n'
        count = 0
        cleaned_breaches = []
        while breaches:
            b = breaches.pop()
            if b[2] == 'breach':
                msg += f'  > {b[1]:.2f} | {b[0]}\n'
                count += 1
            else:
                cleaned_breaches.append(b)

        if count == 0:
            msg += ' > None\n'
        print(msg, end='\n\n')
        breaches = cleaned_breaches

    if len(breaches) > 0:
        msg = f'The following level have been tested:\n'
        count = 0
        cleaned_breaches = []
        while breaches:
            b = breaches.pop()
            if b[2] == 'testing':
                msg += f' - {b[1]:.2f} | {b[0]}\n'
                count += 1
            else:
                cleaned_breaches.append(b)

        if count == 0:
            msg += ' > None\n'
        print(msg)

    Ut.print_ok('All done!')
