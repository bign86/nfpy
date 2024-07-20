#
# Check Sanity of Downloads
# Performs sanity checks on the Download and Import tables to check that there
# are no errors or wrong data.
#

from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO.Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Check sanity of downloads script >>>"


# FIXME: this cannot be done in a query due to the difficulty of it. For example
#        SyntheticFinancials do not have a direct download, but need at least
#        one of Financials type and may have many.
def check_download_exist(_db) -> None:
    q = """
    SELECT
        i.uid, i.ticker, i.provider,
        i.item, d.page, d.currency,
        d.update_frequency, d.last_update,
        d.active AS download_active,
        i.active AS import_active
    FROM Imports AS i
    JOIN Providers AS p
        ON p.provider = i.provider AND p.item = i.item
    JOIN Downloads AS d
        ON i.ticker = d.ticker AND i.provider = d.provider AND p.page = d.page
    WHERE i.active = 1 AND d.active = 0;
    """

    orphan_imp = _db.execute(q).fetchall()

    print(
        f'{Ut.Col.HEADER.value}>>> CHECK DOWNLOADS CONSISTENCY{Ut.Col.ENDC.value}\n'
        f'    Checks that an active download exists for each active import.\n'
        f'    Imported items not actively connected to a download are reported.'
    )
    if len(orphan_imp) == 0:
        print(f'{Ut.Col.OKGREEN.value}None found{Ut.Col.ENDC.value}', end='\n\n')
    else:
        fields = (
            'uid', 'ticker', 'provider', 'item', 'page', 'currency',
            'update_frequency', 'last_update', 'download_active', 'import_active'
        )
        print(
            f'{Ut.Col.FAIL.value}{len(orphan_imp)} found!{Ut.Col.ENDC.value}\n'
            f'{tabulate(orphan_imp, headers=fields, showindex=True)}',
            end='\n\n'
        )


def check_multiple_imports(_db) -> None:
    q = """
    SELECT
        i.uid, i.item,
        SUM(i.active) AS tot_imports
    FROM Imports AS i
    GROUP BY i.uid, i.item 
        HAVING SUM(i.active) > 1;
    """

    wrong_imp = _db.execute(q).fetchall()

    print(
        f'{Ut.Col.HEADER.value}>>> CHECK IMPORTS CONSISTENCY{Ut.Col.ENDC.value}\n'
        f'    Checks that each item is imported exactly once or never. This DOES\n'
        f'    work for Financials as well.'
    )
    if len(wrong_imp) == 0:
        print(f'{Ut.Col.OKGREEN.value}None found{Ut.Col.ENDC.value}', end='\n\n')
    else:
        fields = ('uid', 'item', 'num imports')
        print(
            f'{Ut.Col.FAIL.value}{len(wrong_imp)} found!{Ut.Col.ENDC.value}\n'
            f'{tabulate(wrong_imp, headers=fields, showindex=True)}',
            end='\n\n'
        )


def check_currency_consistency(_db) -> None:
    q = """
    SELECT 
        uid, type, download_ticker,
        download_provider, download_page,
        download_active, import_active, 
        asset_ccy, download_ccy
    FROM (
        SELECT
            i.uid, a.type, d.ticker AS download_ticker,
            d.provider AS download_provider,
            d.page AS download_page, d.active AS download_active,
            i.active AS import_active,
            a.currency AS asset_ccy, d.currency AS download_ccy,
            CASE WHEN
                d.currency IS NULL
            THEN 
                IIF(a.currency IS NULL, True, False)
            ELSE
                IIF(d.currency = a.currency, True, False)
            END consistency
        FROM Imports AS i
        JOIN Downloads AS d
            ON i.ticker = d.ticker AND i.provider = d.provider
        JOIN Assets AS a
            ON a.uid = i.uid
        WHERE a.type NOT IN ('Fx', 'Rate')
    ) AS s
    WHERE s.consistency IS False;
    """

    wrong_ccy = _db.execute(q).fetchall()

    print(
        f'{Ut.Col.HEADER.value}>>> CHECK CURRENCY CONSISTENCY{Ut.Col.ENDC.value}\n'
        f'    For each download checks that the currency matches the currency\n'
        f'    reported in the relative asset table. Does not check for Fx and\n'
        f'    Rate that do not have a proper currency defined.\n'
        f'    Only mismatches are reported.'
    )
    if len(wrong_ccy) == 0:
        print(f'{Ut.Col.OKGREEN.value}None found{Ut.Col.ENDC.value}', end='\n\n')
    else:
        fields = (
            'uid', 'type', 'download_ticker', 'download_provider', 'download_page',
            'download_active', 'import_active', 'asset_ccy', 'download_ccy'
        )
        print(
            f'{Ut.Col.FAIL.value}{len(wrong_ccy)} found!{Ut.Col.ENDC.value}\n'
            f'{tabulate(wrong_ccy, headers=fields, showindex=True)}',
            end='\n\n'
        )


def check_equities_have_benchmark(_db) -> None:
    q = """ 
    SELECT
        [uid], [ticker], [isin], [company]
    FROM Equity
    WHERE [index] IS NULL;
    """

    missing_benchmark = _db.execute(q).fetchall()

    print(
        f'{Ut.Col.HEADER.value}>>> CHECK EQUITIES HAVE A BENCHMARK{Ut.Col.ENDC.value}\n'
        f'    For each equity checks that the a default benchmark for the \n'
        f'    market has been defined. Only failing uids are reported.'
    )
    if len(missing_benchmark) == 0:
        print(f'{Ut.Col.OKGREEN.value}None found{Ut.Col.ENDC.value}', end='\n\n')
    else:
        fields = ('uid', 'ticker', 'isin', 'company')
        print(
            f'{Ut.Col.FAIL.value}{len(missing_benchmark)} found!{Ut.Col.ENDC.value}\n'
            f'{tabulate(missing_benchmark, headers=fields, showindex=True)}',
            end='\n\n'
        )


def check_loose_equities(_db):
    q = """
    SELECT
        [uid], [ticker], [isin], [company]
    FROM [Equity]
    WHERE [uid] NOT IN (
        SELECT DISTINCT [equity]
        FROM [Company]
    );
    """

    loose_equity = _db.execute(q).fetchall()

    print(
        f'{Ut.Col.HEADER.value}>>> CHECK EQUITIES HAVE AN ASSOCIATED COMPANY{Ut.Col.ENDC.value}\n'
        f'    For each equity checks that an associated company has been defined\n'
        f'    Only failing uids are reported.'
    )
    if len(loose_equity) == 0:
        print(f'{Ut.Col.OKGREEN.value}None found{Ut.Col.ENDC.value}', end='\n\n')
    else:
        fields = ('uid', 'ticker', 'isin', 'company')
        print(
            f'{Ut.Col.FAIL.value}{len(loose_equity)} found!{Ut.Col.ENDC.value}\n'
            f'{tabulate(loose_equity, headers=fields, showindex=True)}',
            end='\n\n'
        )


def check_loose_companies(_db):
    q = """
    SELECT
        [uid], [name], [equity]
    FROM [Company]
    WHERE [uid] NOT IN (
        SELECT DISTINCT [company]
        FROM [Equity]
    );
    """

    loose_company = _db.execute(q).fetchall()

    print(
        f'{Ut.Col.HEADER.value}>>> CHECK COMPANIES HAVE AN ASSOCIATED EQUITY{Ut.Col.ENDC.value}\n'
        f'    For each company checks that an associated equity has been defined\n'
        f'    Only failing uids are reported.'
    )
    if len(loose_company) == 0:
        print(f'{Ut.Col.OKGREEN.value}None found{Ut.Col.ENDC.value}', end='\n\n')
    else:
        fields = ('uid', 'name', 'equity')
        print(
            f'{Ut.Col.FAIL.value}{len(loose_company)} found!{Ut.Col.ENDC.value}\n'
            f'{tabulate(loose_company, headers=fields, showindex=True)}',
            end='\n\n'
        )


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()

    # FIXME: disabled because not working
    # check_download_exist(db)
    check_multiple_imports(db)
    check_currency_consistency(db)
    check_equities_have_benchmark(db)
    check_loose_equities(db)
    check_loose_companies(db)

    Ut.print_ok('All done!')
