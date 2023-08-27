#
# Search Equity without Benchmark
# Finds equities that do not have a reference index set.
#

import nfpy.Calendar as Cal
import nfpy.DB as DB
from nfpy.Tools import Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Search Equity without Benchmark Script >>>"

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    cal = Cal.get_calendar_glob()
    cal.initialize(
        Cal.today(mode='timestamp'),
        Cal.last_business(2, mode='timestamp')
    )

    # Get all Equity
    q_eq = qb.select('Equity', fields=('uid', 'ticker', 'isin', 'company'),
                     keys=(), where='[index] is NULL')
    eq_list = db.execute(q_eq).fetchall()
    if not eq_list:
        print('No equities without benchmark found...')
    else:
        msg = f">>> Equities without an index\n\n" \
              f"{'uid':^12}: {'ticker':^8}\t{'isin':^12}\t{'company':^8}\n" \
                f"------------------------------------------------\n"
        for eq in eq_list:
            msg += f'{eq[0]:^12}: {eq[1]:^8}\t{eq[2]:^12}\t{eq[3]:^8}'
        print(msg, end='\n\n')

    Ut.print_ok('All done!')
