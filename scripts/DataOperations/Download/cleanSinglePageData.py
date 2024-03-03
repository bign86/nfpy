#
# Clean single page data
# Clean data relative to a single downloading page.
# Allows to specify a (provider, page, ticker) tuple and delete all data
# connected to such tuple.
#

import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

__version__ = '0.1'
_TITLE_ = "<<< Clean single page data script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    conf = get_conf_glob()
    dwn = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    params, prov_obj = (), None
    while True:
        # Choose the provider
        providers = tuple(dwn.providers)
        Ut.print_sequence(providers, showindex=True)
        prov_idx = inh.input(
            "Give the provider index: ",
            idesc='index', limits=(0, len(providers) - 1)
        )
        provider = providers[prov_idx]

        # Choose the page
        pages = dwn.pages(provider)
        Ut.print_sequence(pages, showindex=True)
        pg_idx = inh.input(
            "Give the download page index: ",
            idesc='index', limits=(0, len(pages) - 1)
        )
        page = pages[pg_idx]

        # Get ticker
        ticker = inh.input("Ticker to clean: ", idesc='str')

        # Check existence
        dwn_keys = ('provider', 'page', 'ticker')
        params = (provider, page, ticker)
        q = qb.select('Downloads', keys=dwn_keys)
        res = db.execute(q, params).fetchall()
        if not res:
            print('Download not found', end='\n\n')
        else:
            break

    page = prov_obj.create_page_obj(*params[1:])
    q_del = qb.delete(page.table, fields=('ticker',))

    if inh.input(f'The query to be executed:\n{q_del}\nProceed?: ',
                 idesc='bool', default=False):
        DB.backup_db()
        db.execute(q_del, p=(params[2],), commit=True)
    else:
        print('Aborted!', end='\n\n')

    print('All done!')
