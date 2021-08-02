#
# Search Loose Stocks
#

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.Tools.Utilities as Ut

__version__ = '0.1'
_TITLE_ = "<<< Search Loose Stocks Script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    cal = Cal.get_calendar_glob()
    cal.initialize(
        Cal.today(mode='timestamp'),
        Cal.last_business(2, mode='timestamp')
    )

    # Equities
    print('>>> Equities')
    q_eq = qb.select(
        'Equity',
        fields=('uid', 'ticker', 'isin', 'company'),
        keys=(),
        where='uid not in (select distinct [equity] from Company)'
    )
    eq_list = db.execute(q_eq).fetchall()
    if not eq_list:
        print('No loose equities found...')
    else:
        eq_dict = Ut.list_to_dict(eq_list)
        msg = f"{'uid':^12}: {'ticker':^8}\t{'isin':^12}\t{'company':^8}\n"
        for eq, data in eq_dict.items():
            msg += f'{eq:12}: {data[0]:8}\t{data[1]:12}\t{data[2]:8}\n'
        print(msg, end='\n\n')

    # Companies
    print('>>> Companies')
    q_cmp = qb.select(
        'Company',
        fields=('uid', 'name', 'equity'),
        keys=(),
        where='uid not in (select distinct [company] from Equity)'
    )
    cmp_list = db.execute(q_cmp).fetchall()
    if not cmp_list:
        print('No loose companies found...')
    else:
        cmp_dict = Ut.list_to_dict(cmp_list)
        msg = "{'uid':^12}: {'name':^8}\t{'equity':^8}\n"
        for cmp, data in cmp_dict.items():
            msg += f'{cmp:12}: {data[0]:8}\t{data[1]:8}\n'
        print(msg, end='\n\n')

    print('All done!')
