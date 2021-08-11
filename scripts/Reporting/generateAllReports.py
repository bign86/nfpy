#
# Create report
# Run the report engine on all automatic reports
#

from pandas import DateOffset

from nfpy.Calendar import (get_calendar_glob, today)
from nfpy.Reporting import get_re_glob

__version__ = '0.2'
_TITLE_ = "<<< Report generation script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    end = today(mode='timestamp')
    start = end - DateOffset(months=120)
    cal.initialize(end, start)

    get_re_glob().run(active=True)

    print('All done!')
