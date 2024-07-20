#
# Re-download Single Asset
# Script to download from internet a single asset from scratch
#

from tabulate import tabulate

import nfpy.Downloader as Dwn
import nfpy.IO as IO
import nfpy.IO.Utilities as Ut

__version__ = '0.1'
_TITLE_ = "<<< Download single asset script >>>"
__desc__ = """
The script allows the user to select a single download and save the
data to database.
"""

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    dwnf = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    downloads = ()
    while True:
        ticker = inh.input("Give a ticker: ", idesc='str')
        downloads = dwnf.fetch_downloads(ticker=ticker)
        if not downloads:
            Ut.print_warn(f'{Ut.Col.WARNING.value}Supplied ticker does not exist! Please give a valid one.{Ut.Col.ENDC.value}')
        else:
            break

    tab = tabulate(
        [(v.provider, v.page, v.ticker, v.currency) for v in downloads],
        headers=('Provider', 'Page', 'Ticker', 'CCY'), showindex=True
    )
    idx = inh.input(
        f'{tab}\nChoose a list of indices for download: ',
        idesc='uint', is_list=True
    )

    for i in idx:
        dwn = downloads[i]
        dwnf.run_download(
            do_save=True,
            override_date=True,
            provider=dwn.provider,
            page=dwn.page,
            ticker=ticker,
            override_active=True
        )

    Ut.print_ok('All done!')
