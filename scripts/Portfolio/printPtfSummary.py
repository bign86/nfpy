#
# Print Portfolio Summary Script
# Print a summary of the content of a portfolio
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Constants as Cn

__version__ = '0.5'
_TITLE_ = "<<< Print portfolio summary script >>>"

_FMT_ = '%Y-%m-%d'

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    af = get_af_glob()
    inh = IO.InputHandler()

    calendar = Cal.get_calendar_glob()
    end = Cal.today(mode='timestamp')
    start = Cal.shift(end, -2 * Cn.DAYS_IN_1Y, 'D')

    start = inh.input(f"Give an start date (default {start.strftime(_FMT_)}): ",
                      idesc='timestamp', default=start, optional=True)

    calendar.initialize(end=end, start=start)

    # Get portfolio
    q = "select * from Assets where type = 'Portfolio'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print(f'\n\nAvailable portfolios:\n'
          f'{tabulate(res, headers=f, showindex=True)}',
          end='\n\n')
    idx = inh.input("Give a portfolio index: ", idesc='int')
    ptf_uid = res[idx][0]

    ptf = af.get(ptf_uid)
    res = ptf.summary()

    print(f'\n *** Portfolio info ***\n------------------------\n'
          f'Uid:\t\t{res["uid"]}\n'
          f'Currency:\t{res["currency"]}\n'
          f'Date:\t\t{res["date"].strftime(_FMT_)}\n'
          f'Inception:\t{res["inception"].strftime(_FMT_)}\n'
          f'Tot. Value:\t{res["tot_value"]:.2f}',
          end='\n\n')

    print(' *** Summary of positions ***\n------------------------------\n')
    df = res['constituents_data']
    print(df.to_string(index=False,
                       float_format=lambda x: '{:.2f}'.format(x),
                       formatters={'quantity': '{:,.0f}'.format}))

    print("All done!")
