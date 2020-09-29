#
# Print Portfolio Summary Script
# Print a summary of the content of a portfolio
#

from tabulate import tabulate
from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Handlers.Calendar import get_calendar_glob, today
from nfpy.Portfolio.PortfolioManager import PortfolioManager
from nfpy.Tools.Constants import BDAYS_IN_1Y
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.1'
_TITLE_ = "<<< Print portfolio summary script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    af = get_af_glob()
    inh = InputHandler()
    pm = PortfolioManager()

    cal = get_calendar_glob()
    end = today(mode='timestamp')
    start = cal.shift(end, BDAYS_IN_1Y, False)
    cal.initialize(end=end, start=start)

    # Get equity
    q = "select * from Assets where type = 'Portfolio'"
    f = list(qb.get_fields('Assets'))
    res = db.execute(q).fetchall()

    print('\n\nAvailable portfolios:')
    print(tabulate(res, headers=f, showindex=True))
    uid = inh.input("\nGive a portfolio index: ", idesc='int')
    ptf_uid = res[uid][0]

    ptf = af.get(ptf_uid)
    f, d = pm.summary(ptf)

    print('\n *** Portfolio info ***\n------------------------\n')
    print('uid:\t\t{}\nCurrency:\t{}\nDate:\t\t{}'
          .format(ptf_uid, ptf.base_currency, ptf.date))

    print('\n\n *** Summary of positions ***\n------------------------------\n')
    print(tabulate(d, headers=f))
    print(end='\n\n')

    print("All done!")
