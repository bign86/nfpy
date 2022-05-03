#
# Download Single Asset
# Script to download from internet a single page
#

from tabulate import tabulate

from nfpy.Calendar import today
import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.6'
_TITLE_ = "<<< Download single asset script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    f = Dwn.get_dwnf_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    is_ticker_valid = False
    data = ()
    while not is_ticker_valid:
        ticker = inh.input("Give a ticker to download for: ", idesc='str')
        data = f.fetch_downloads(ticker=ticker, active=False)
        if not data:
            print('*** Supplied ticker does not exist! Please give a valid one.')
        else:
            is_ticker_valid = True

    fields = qb.get_fields(f.download_table)
    tab = tabulate(data, headers=fields, showindex=True)
    print(tab, end='\n\n')
    choice = inh.input('Index: ', idesc='int')
    while 0 > choice >= len(data):
        print('*** Invalid index! ***')
        choice = inh.input('Index: ', idesc='int')

    dwn = data[choice]
    p = f.create_page_obj(dwn[1], dwn[2], dwn[3])
    num_params = f.print_parameters(p)

    params = {}
    if num_params > 0:
        msg = "Type the additional parameters as key1, value1, key2, value2, ...:\n"
        pin = inh.input(msg, idesc='str', is_list=True, default=[])
        params = Ut.list_to_dict(pin)

    p.initialize(dwn[4], params=params)
    p.fetch()
    p.printout()

    if inh.input('\nSave the results to database?', idesc='bool', default=False):
        p.save()
        # TODO: write a logic inside the download factory to get rid of this
        #       external logic here. We don't want to deal with QueryBuilder and
        #       database directly but hand off to the DownloadFactory
        data_upd = (today(), dwn[1], dwn[2])
        q_upd = qb.merge('Downloads', fields=['last_update'])
        db.execute(q_upd, data_upd, commit=True)

    print('All done!')
