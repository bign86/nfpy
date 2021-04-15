#
# Print Portfolio Summary Script
# Print a summary of the content of a portfolio
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.IO as IO
from nfpy.Tools import Constants as Cn

__version__ = '0.5'
_TITLE_ = "<<< Print portfolio summary script >>>"

_FMT_ = '%Y-%m-%d'

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = IO.get_db_glob()
    qb = IO.get_qb_glob()
    af = get_af_glob()
    inh = IO.InputHandler()

    calendar = Cal.get_calendar_glob()
    end = Cal.today(mode='timestamp')
    start = Cal.shift(end, -2 * Cn.DAYS_IN_1Y, 'D')

    msg = "Give an start date (default {}): "
    start = inh.input(msg.format(start.strftime(_FMT_)), idesc='timestamp',
                      default=start, optional=True)

    calendar.initialize(end=end, start=start)

    # Get portfolio
    q = "select * from Assets where type = 'Portfolio'"
    f = list(qb.get_fields('Assets'))
    res = db.execute(q).fetchall()

    print('\n\nAvailable portfolios:')
    print(tabulate(res, headers=f, showindex=True))
    idx = inh.input("\nGive a portfolio index: ", idesc='int')
    ptf_uid = res[idx][0]

    ptf = af.get(ptf_uid)
    res = ptf.summary()

    print('\n *** Portfolio info ***\n------------------------\n')
    print('Uid:\t\t{}\nCurrency:\t{}\nDate:\t\t{}\nInception:\t{}\nTot. Value:\t{:.2f}'
          .format(res['uid'], res['currency'], res['date'].strftime(_FMT_),
                  res['inception'].strftime(_FMT_), res['tot_value']))

    print('\n\n *** Summary of positions ***\n------------------------------\n')
    df = res['constituents_data']
    print(df.to_string(index=False,
                       float_format=lambda x: '{:.2f}'.format(x),
                       formatters={'quantity': '{:,.0f}'.format}))

    print("All done!")
