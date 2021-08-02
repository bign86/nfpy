#
# Search Equity without Benchmark
# Search for equities and without a default index
#

import nfpy.Calendar as Cal
import nfpy.DB as DB

__version__ = '0.1'
_TITLE_ = "<<< Search Equity without Benchmark Script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

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
        msg = f">>> Equities without an index\n\n'" \
              f"{'uid':12}: {'ticker':8}\t{'isin':12}\t{'company':8}"
        for eq in eq_list:
            msg += f'{eq[0]:12}: {eq[1]:8}\t{eq[2]:12}\t{eq[3]:8}'
        print(msg, end='\n\n')

    print('All done!')
