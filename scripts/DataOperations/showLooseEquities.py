#
# Search Loose Stocks
# Finds equities for which no company has been set and companies for which no
# equity has been set.
#

import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.Tools.Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Search Loose Stocks Script >>>"

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    cal = Cal.get_calendar_glob()
    cal.initialize(
        Cal.today(mode='timestamp'),
        Cal.last_business(2, mode='timestamp')
    )

    # Equities
    Ut.print_header('>>> Equities')
    q_eq = qb.select(
        'Equity',
        fields=('uid', 'ticker', 'isin', 'company'),
        keys=(),
        where='uid not in (select distinct [equity] from Company)'
    )
    eq_list = db.execute(q_eq).fetchall()
    if not eq_list:
        Ut.print_ok('No loose equities found...', end='\n\n')
    else:
        eq_dict = Ut.list_to_dict(eq_list)
        msg = f"{'uid':^12}: {'ticker':^8}\t{'isin':^12}\t{'company':^8}\n"
        for eq, data in eq_dict.items():
            msg += f'{eq:12}: {data[0]:8}\t{data[1]:12}\t{data[2]:8}\n'
        print(msg, end='\n\n')

    # Companies
    Ut.print_header('>>> Companies')
    q_cmp = qb.select(
        'Company',
        fields=('uid', 'name', 'equity'),
        keys=(),
        where='uid not in (select distinct [company] from Equity)'
    )
    cmp_list = db.execute(q_cmp).fetchall()
    if not cmp_list:
        Ut.print_ok('No loose companies found...', end='\n\n')
    else:
        cmp_dict = Ut.list_to_dict(cmp_list)
        msg = f"{'uid':^8}: {'name':^25}\t{'equity':^12}\n"
        for cmp, data in cmp_dict.items():
            msg += f'{cmp:8}: {data[0]:25}\t{data[1]:12}\n'
        print(msg, end='\n\n')

    Ut.print_ok('All done!')
