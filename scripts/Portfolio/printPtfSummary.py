#
# Print Portfolio Summary Script
# Print a summary of the content of a portfolio
#

import pandas as pd
from tabulate import tabulate

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.DB as DB
from nfpy.Financial.Portfolio import PortfolioEngine
import nfpy.IO as IO

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}

__version__ = '0.6'
_TITLE_ = "<<< Print portfolio summary script >>>"

_FMT_ = '%Y-%m-%d'

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    af = get_af_glob()
    inh = IO.InputHandler()

    # Get portfolio choice from the user
    q = "select * from Assets where type = 'Portfolio'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print(f'\nAvailable portfolios:\n'
          f'{tabulate(res, headers=f, showindex=True)}',
          end='\n\n')
    idx = inh.input("Give a portfolio index: ", idesc='int')
    ptf_uid = res[idx][0]

    # Since when we create the portfolio object we need to have a calendar done,
    # here we read the inception date ahead of creating the portfolio.
    q = f"select inception_date from Portfolio where uid = '{ptf_uid}'"
    inception = db.execute(q).fetchone()[0]

    calendar = Cal.get_calendar_glob()
    end = Cal.today(mode='timestamp')
    calendar.initialize(end=end, start=inception)

    # Load the portfolio and print the summary
    ptf = af.get(ptf_uid)
    pe = PortfolioEngine(ptf)
    res = pe.summary()

    print(f'\n *** Portfolio info ***\n------------------------\n'
          f'Uid:\t\t{res["uid"]}\n'
          f'Currency:\t{res["currency"]}\n'
          f'Inception:\t{res["inception"].strftime(_FMT_)}\n'
          f'Tot. Value:\t{res["tot_value"]:.2f}',
          end='\n\n')

    df = res['constituents_data']
    print(' *** Summary of positions ***\n------------------------------\n')
    print(df.to_string(
        index=False,
        float_format=lambda x: '{:.2f}'.format(x),
        formatters={'quantity': '{:,.0f}'.format},
        **PD_STYLE_PROP
    ),
        end='\n\n'
    )

    dt, divs = pe.dividends_received_yearly()
    msg = f' *** History of received dividends\n------------------------------\n'
    for i in range(len(dt)):
        msg += f'{dt[i]}: {round(divs[i], 2)}\n'
    print(msg)

    print("All done!")
