#
# Clean triggered manual alerts
# Script to clean from database the triggered manual alerts
#

import nfpy.Calendar as Cal
import nfpy.IO as IO
import nfpy.Trading as Trd

__version__ = '0.1'
_TITLE_ = '<<< Clean triggered manual alerts script >>>'


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    ae = Trd.AlertsEngine()
    cal = Cal.get_calendar_glob()
    inh = IO.InputHandler()

    cal.initialize(Cal.today(), Cal.last_business())

    # Get triggered alerts
    to_rem = ae.fetch(triggered=True)

    msg = f'The following have been found:\n'
    for a in to_rem:
        msg += f'  * {a.uid} @ P {">" if a.cond=="G" else "<="} {a.value} ' \
               f'=> triggered: {a.date_triggered}\n'
    msg += f'Continue with removal?: '
    if inh.input(msg, idesc='bool'):
        print('   * Deleting...', end='\n\n')
        ae.remove(to_rem)
    else:
        print('   * Aborted', end='\n\n')

    print('All done!')
