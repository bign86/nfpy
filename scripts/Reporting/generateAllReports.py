#
# Create report
# Run the report engine on all automatic reports
#

from pandas import DateOffset

from nfpy.Handlers.Calendar import get_calendar_glob, today
from nfpy.Reporting.ReportingEngine import ReportingEngine

__version__ = '0.1'
_TITLE_ = "<<< Report generation script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    end = today(mode='timestamp')
    start = end - DateOffset(years=10)
    cal.initialize(end, start)

    ReportingEngine().run()

    print('All done!')
