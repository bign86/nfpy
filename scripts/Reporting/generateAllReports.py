#
# Produce all automatic reports
# Run the report engine on all automatic reports
#

from pandas import DateOffset

from nfpy.Calendar import today
import nfpy.IO.Utilities as Ut
from nfpy.Reporting import ReportingEngine
from nfpy.Session import get_session

__version__ = '0.3'
_TITLE_ = "<<< All reports generation script >>>"

_TIME_SPAN_MONTH = 120

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    s = get_session()
    end = today(mode='timestamp')
    start = end - DateOffset(months=_TIME_SPAN_MONTH)
    s.initialize(end, start)

    ReportingEngine(end).run(active=True)

    Ut.print_ok('All done!')
