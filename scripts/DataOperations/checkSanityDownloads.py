#
# Check Sanity of Downloads
# Performs sanity checks on the Download and Import tables to check that there
# are no errors or wrong data.
#

from tabulate import tabulate

import nfpy.DB as DB
from nfpy.Tools.Utilities import Col

__version__ = '0.1'
_TITLE_ = "<<< Check sanity of downloads script >>>"


def check_download_exist(_db) -> None:
    q = """select i.uid, i.ticker, i.provider, i.item, d.page, d.currency,
        d.update_frequency, d.last_update, d.active as download_active,
        i.active as import_active from Imports as i join Providers as p
        on p.provider = i.provider and p.item = i.item join Downloads as d
        on i.ticker = d.ticker and i.provider = d.provider and p.page = d.page
        where i.active = 1 and d.active = 0"""

    orphan_imp = _db.execute(q).fetchall()

    print(
        f'>>> Checks that an active download exists for each active import.\n'
        f'    Imported items not actively connected to a download are reported.'
    )
    if len(orphan_imp) == 0:
        print(f'{Col.OKGREEN.value}None found{Col.ENDC.value}', end='\n\n')
    else:
        fields = (
            'uid', 'ticker', 'provider', 'item', 'page', 'currency',
            'update_frequency', 'last_update', 'download_active', 'import_active'
        )
        print(
            f'{Col.FAIL.value}{len(orphan_imp)} found!{Col.ENDC.value}\n'
            f'{tabulate(orphan_imp, headers=fields, showindex=True)}',
            end='\n\n'
        )


def check_imports_consistency(_db) -> None:
    q = """select i.uid, i.item, sum(i.active) as tot_imports from Imports as i
        where (i.provider != 'Investing' and i.item != 'Financials')
        group by i.uid, i.item having sum(i.active) > 1"""

    wrong_imp = _db.execute(q).fetchall()

    print(
        f'>>> Checks that each item is imported ones.\n'
        f'    For each uid and each imported item, only one active download\n'
        f'    should be present. This does NOT work for Investing Financials\n'
        f'    that are currently excluded from the test.'
    )
    if len(wrong_imp) == 0:
        print(f'{Col.OKGREEN.value}None found{Col.ENDC.value}', end='\n\n')
    else:
        fields = ('uid', 'item', 'num imports')
        print(
            f'{Col.FAIL.value}{len(wrong_imp)} found!{Col.ENDC.value}\n'
            f'{tabulate(wrong_imp, headers=fields, showindex=True)}',
            end='\n\n'
        )


def check_currency_consistency(_db) -> None:
    q = """select uid, count(*) from (select distinct i.uid,
    d.currency as ccy_dwn, a.currency as ccy_elab from Imports as i
    join Downloads as d on i.ticker = d.ticker and i.provider = d.provider
    join Assets as a on a.uid = i.uid where d.active = 1 and i.active = 1
    ) as s group by uid having count(*) > 1"""

    wrong_ccy = _db.execute(q).fetchall()

    print(
        f'>>> Checks the downloads for each asset have the right currency.\n'
        f'    For each uid the downloads and elaboration currencies should\n'
        f'    match. Mismatches are reported.'
    )
    if len(wrong_ccy) == 0:
        print(f'{Col.OKGREEN.value}None found{Col.ENDC.value}', end='\n\n')
    else:
        fields = ('uid', 'num ccy combinations')
        print(
            f'{Col.FAIL.value}{len(wrong_ccy)} found!{Col.ENDC.value}\n'
            f'{tabulate(wrong_ccy, headers=fields, showindex=True)}',
            end='\n\n'
        )


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()

    check_download_exist(db)
    check_imports_consistency(db)
    check_currency_consistency(db)

    print("All done!")
