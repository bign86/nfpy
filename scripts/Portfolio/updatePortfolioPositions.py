#
# Update Portfolio Positions Script
# Script to add or remove trades from portfolios.
#

from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Calendar import get_calendar_glob, today
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.2'
_TITLE_ = "<<< Update portfolio positions script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    cal = get_calendar_glob()
    inh = InputHandler()

    start = inh.input("Give a start date: ", idesc='timestamp')
    end = inh.input("Give an end date (default today): ",
                    idesc='timestamp', default=today(mode='timestamp'),
                    optional=True)
    cal.initialize(end, start=start)

    uid = inh.input("Give a portfolio uid: ", idesc='str', checker='uid')
    ptf = af.get(uid)

    print('Portfolio @ {}'.format(ptf.date))
    print('Portfolio constituents [{}]:\n{}'.format(ptf.num_constituents,
                                                    ptf.constituents_uids))
    print('Portfolio value: {:.2f} {}'.format(ptf.total_value.iat[-1], ptf.currency))

    save = inh.input("\nSave the new portfolio positions (default No)?: ",
                     idesc='bool', default=False, optional=True)
    if save:
        print('Saving...')
        ptf.write_cnsts()

    print("All done!")
