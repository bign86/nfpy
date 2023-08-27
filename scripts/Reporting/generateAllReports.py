#
# Produce all automatic reports
# Run the report engine on all automatic reports
#

from pandas import DateOffset

from nfpy.Calendar import (get_calendar_glob, today)
from nfpy.Reporting import get_re_glob
from nfpy.Tools import Utilities as Ut

__version__ = '0.3'
_TITLE_ = "<<< All reports generation script >>>"

_TIME_SPAN_MONTH = 120

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    end = today(mode='timestamp')
    start = end - DateOffset(months=_TIME_SPAN_MONTH)
    cal.initialize(end, start)

    get_re_glob().run(active=True)

    Ut.print_ok('All done!')
