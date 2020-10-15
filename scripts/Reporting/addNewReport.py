#
# Add new report
# Add a new report to the database
#

from nfpy.Handlers.Calendar import get_calendar_glob, today, last_business
from nfpy.Handlers.Inputs import InputHandler
from nfpy.Reporting.ReportingEngine import ReportingEngine

__version__ = '0.1'
_TITLE_ = "<<< New report add script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    cal.initialize(today(), last_business())

    inh = InputHandler()
    re = ReportingEngine()

    # Create model object from input
    uid = inh.input("Insert UID: ")
    m = inh.input("Insert model: ")
    try:
        m_obj = re.get_report_obj(m)
    except KeyError:
        raise KeyError('Model {} not recognized'.format(m))

    # Ask user for parameters
    params = {}
    for p, q, kw in m_obj.INPUT_QUESTIONS:
        v = inh.input(q, **kw)
        if v:
            params[p] = v

    # Put in auto?
    active = inh.input("Set 'active' flag? (default False): ",
                       idesc='bool', default=False)

    # Add to table
    re.add(uid, m, params, active)

    print('All done!')
