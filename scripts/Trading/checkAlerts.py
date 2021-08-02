#
# Check manual alerts
# Script to check for triggered manual alerts for an instrument
#

from datetime import timedelta

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.Trading as Trd

__version__ = '0.1'
_TITLE_ = '<<< Check manual alerts script >>>'

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    ae = Trd.AlertsEngine()
    db = DB.get_db_glob()
    cal = Cal.get_calendar_glob()
    inh = IO.InputHandler()

    end = Cal.today(mode='datetime')
    start = end - timedelta(days=90)
    cal.initialize(end=end, start=start)

    # Get input
    uids = inh.input('Give the list of uids to check. Leave empty to check all: ',
                     optional=True, is_list=True)
    days = inh.input('Time window for check in days: ', idesc='int')
    window = end - timedelta(days=days)

    # If no uid is given, take them all
    if uids is None:
        uids = [
            u[0] for u in
            db.execute(
                'select distinct uid from Alerts'
            ).fetchall()
        ]
        if not uids:
            print('No alerts found in the database.')
            exit()

    # Check for triggered alerts
    breached = ae.raise_alerts(
        uids,
        date_checked=window
    )

    msg = f'New breaches detected:\n'
    for b in breached:
        msg += f'  > {b.uid}: p {">" if b.cond == "G" else "<"} {b.value}\n'
    print(msg)

    # Check for all breaches
    all_b = ae.fetch(
        uids,
        triggered=True,
        date_triggered=window
    )

    msg = f'All breaches detected in the last {days} days:\n'
    for a in all_b:
        msg += f'  > {a.uid}: p {">" if a.cond == "G" else "<"} {a.value} ' \
               f'@ {a.date_triggered.strftime("%Y-%m-%d")}\n'
    print(msg)

    print('All done!')
