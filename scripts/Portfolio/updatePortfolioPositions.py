#
# Update Portfolio Positions Script
# Script to add or remove trades from portfolios.
#

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.IO as IO

__version__ = '0.3'
_TITLE_ = "<<< Update portfolio positions script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    cal = get_calendar_glob()
    inh = IO.InputHandler()

    start = inh.input("Give a start date: ", idesc='timestamp')
    end = inh.input("Give an end date (default today): ",
                    idesc='timestamp',
                    default=today(mode='timestamp'),
                    optional=True)
    cal.initialize(end, start=start)

    uid = inh.input("Give a portfolio uid: ", idesc='str', checker='uid')
    ptf = af.get(uid)

    print(f'Portfolio @ {ptf.date}'
          f'Portfolio constituents [{ptf.num_constituents}]:\n{ptf.constituents_uids}'
          f'Portfolio value: {ptf.total_value.iat[-1]:.2f} {ptf.currency}',
          end='\n\n')

    save = inh.input("Save the new portfolio positions (default No)?: ",
                     idesc='bool', default=False, optional=True)
    if save:
        print('Saving...')
        ptf.write_cnsts()

    print("All done!")
