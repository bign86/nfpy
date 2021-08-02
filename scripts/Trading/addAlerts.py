#
# Add manual alerts
# Script to add a new manual alert for an instrument
#

from datetime import timedelta

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.IO as IO
import nfpy.Trading as Trd

__version__ = '0.1'
_TITLE_ = '<<< Add manual alerts script >>>'


def add_alert():
    # Get uid
    uid = inh.input('Give an uid for the new alert: ', checker='uid')
    p = inh.input('Give a price: ', idesc='float')

    # Search for info
    lp = lp_dict.get(uid, None)
    if not lp:
        lp = af.get(uid) \
            .last_price()[0]
        lp_dict[uid] = lp

    # Build Alert tuple
    al = Trd.Alert(
        uid, end,
        'L' if p < lp else 'G',
        p, False, None, None
    )
    to_write.append(al)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = Ast.get_af_glob()
    ae = Trd.AlertsEngine()
    cal = Cal.get_calendar_glob()
    inh = IO.InputHandler()

    end = Cal.today(mode='datetime')
    start = end - timedelta(days=90)
    cal.initialize(end=end, start=start)

    # Working variables: storage of last prices, final list
    lp_dict = {}
    to_write = []

    # First item
    add_alert()

    # While forever until done
    while inh.input('\nAdd another?: ', idesc='bool'):
        add_alert()

    # Save into database
    if len(to_write) > 0:
        msg = f'\nAdding {len(to_write)} new alerts:\n'
        for a in to_write:
            msg += f'  * {a.uid} @ P {">=" if a.cond=="G" else "<"} {a.value}\n'
        msg += f'Continue?: '
        if inh.input(msg, idesc='bool'):
            print('  * Writing', end='\n\n')
            ae.add(to_write)
        else:
            print('  * Aborted!', end='\n\n')
    else:
        print('\nNothing to write', end='\n\n')

    print('All done!')
