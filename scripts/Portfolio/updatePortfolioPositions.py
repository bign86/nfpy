#
# Update Portfolio Positions Script
# Script to add or remove trades from portfolios.
#

import datetime
from tabulate import tabulate

from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Calendar import get_calendar_glob, today_
from nfpy.Portfolio.PortfolioManager import PortfolioManager
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.1'
_TITLE_ = "<<< Update portfolio positions script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    cal = get_calendar_glob()
    inh = InputHandler()

    end = today_(string=False) - datetime.timedelta(days=80)
    start = (end - datetime.timedelta(days=365))
    cal.initialize(end, start)

    uid = inh.input("\nGive a portfolio uid: ", idesc='str')
    ptf = af.get(uid)
    ptf.load()

    print('\n * Calendar dates: {} - {}\n'.format(start, end))
    pm = PortfolioManager()

    print('Portfolio @ {}'.format(ptf.date))
    print('Portfolio constituents:')
    f, data = pm.portfolio_summary(ptf)
    print(tabulate(data, headers=f, showindex=True))

    print('\n---------------------------------')
    print('Updating...')
    pm.update(ptf)
    print('---------------------------------\n')

    print('Portfolio @ {}'.format(ptf.date))
    print('Portfolio constituents:')
    f, data = pm.portfolio_summary(ptf)
    print(tabulate(data, headers=f, showindex=True))

    save = inh.input("\nSave the new portfolio positions (default No)?: ",
                     idesc='bool', default=False)
    if save:
        print('Saving...')
        ptf.write_cnsts()

    print("All done!")
