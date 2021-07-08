#
# Clean downloaded data
# Clean data data relative to a single downloading page
#

import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

__version__ = '0.1'
_TITLE_ = "<<< Clean downloaded data script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    conf = get_conf_glob()
    dwn = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    params, prov_obj = (), None
    while True:
        # Get provider
        providers, prov_idx = tuple(dwn.providers), -1
        Ut.print_sequence(providers, showindex=True)
        while prov_idx < 0 or prov_idx > len(providers):
            prov_idx = inh.input("Give the provider index: ", idesc='int')
        provider = providers[prov_idx]

        # Page
        prov_obj = dwn.get_provider(provider)
        pages, pg_idx = tuple(prov_obj.pages), -1
        Ut.print_sequence(pages, showindex=True)
        while pg_idx < 0 or pg_idx > len(pages):
            pg_idx = inh.input("Give the download page index: ", idesc='int')
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

    print('The query to be executed:\n{}'.format(q_del))
    if inh.input('Proceed?: ', idesc='bool', default=False):
        DB.backup_db()
        db.execute(q_del, p=(params[2],), commit=True)
    else:
        print('Aborted!', end='\n\n')

    print('All done!')
