#
# Clean single page data
# Clean data relative to a single downloading page.
# Allows to specify a (provider, page, ticker) tuple and delete all data
# connected to such tuple.
#

import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
import nfpy.IO.Utilities as Ut
from nfpy.Tools import (Exceptions as Ex, get_conf_glob)

__version__ = '0.1'
_TITLE_ = "<<< Clean single page data script >>>"
__desc__ = """
The script selects a single download as identified by the tuple
(provider, page, ticker) and deletes all data belonging to the tuple
found in the *download* tables (not in the elaboration tables).
"""

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    conf = get_conf_glob()
    dwn = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    # Choose the provider
    providers = sorted(dwn.providers)
    Ut.print_sequence(providers, showindex=True)
    prov_idx = inh.input(
        "Give the provider index: ",
        idesc='index', limits=(0, len(providers) - 1)
    )
    provider = providers[prov_idx]

    # Choose the page
    pages = sorted(dwn.pages(provider))
    Ut.print_sequence(pages, showindex=True)
    pg_idx = inh.input(
        "Give the download page index: ",
        idesc='index', limits=(0, len(pages) - 1)
    )
    page = pages[pg_idx]

    # Get ticker
    ticker = inh.input("Ticker to clean: ", idesc='str')

    # Check existence
    # dwn_keys = ('provider', 'page', 'ticker')
    # q = qb.select('Downloads', keys=dwn_keys)
    # params = (provider, page, ticker)
    # res = db.execute(q, params).fetchall()
    res = dwn.fetch_downloads(
        provider=provider, page=page, ticker=ticker, active=False
    )
    if not res:
        Ut.print_warn('! Download not found', end='\n\n')
        exit()

    # Get the download generator, from it the page and the table to clean up
    _, generator = Dwn.get_provider(provider)() \
        .get_download_generator(res)
    table = [page.table for d, page in generator][0]

    # Execute the cleaning
    q_del = qb.delete(table, fields=('ticker',))
    if inh.input(
            f'The query to be executed:\n\n{q_del}\n\n'
            f'The DB will be backed up.\nProceed?: ',
            idesc='bool', default=False
    ):
        try:
            DB.backup_db()
        except Exception:
            raise Ex.DatabaseError('Failed backup!')
        else:
            db.execute(q_del, p=(ticker,), commit=True)
    else:
        Ut.print_warn('! Aborted!', end='\n\n')

    Ut.print_ok('All done!')
