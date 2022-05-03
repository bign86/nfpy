#
# Add manual alerts
# Script to add a new manual alert for an instrument
#

from datetime import timedelta

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.IO as IO
import nfpy.Trading as Trd

__version__ = '0.2'
_TITLE_ = '<<< Add manual alerts script >>>'


def add_alert(_uid):
    # Get uid
    p = inh.input('Give a price: ', idesc='float')

    # Search for info
    lp = lp_dict.get(_uid, None)
    if not lp:
        lp = af.get(_uid) \
            .last_price()[0]
        lp_dict[_uid] = lp

    # Build Alert tuple
    al = Trd.Alert(
        _uid, end,
        'L' if p < lp else 'G',
        p, False, None, None
    )
    to_write.append(al)


def save():
    if len(to_write) > 0:
        msg = f'\nAdding {len(to_write)} new alerts:\n'
        for a in to_write:
            msg += f'  * {a.uid} @ P {">=" if a.cond == "G" else "<"} {a.value}\n'
        msg += f'Continue?: '
        if inh.input(msg, idesc='bool'):
            print('  * Writing', end='\n\n')
            ae.add(to_write)
        else:
            print('  * Aborted!', end='\n\n')
    else:
        print('\nNothing to write', end='\n\n')
    quit_()


def quit_():
    print('All done!')
    exit()


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

    # While forever until done
    print(
        f"Give a UID for which to add the alert. Input 'save' to save and exit.\n"
        f"Give 'quit' to exit without saving.",
        end='\n\n'
    )
    while True:
        command = inh.input('\n>>> ', idesc='str')
        if command == 'quit':
            quit_()
        elif command == 'save':
            save()
        else:
            add_alert(command)
