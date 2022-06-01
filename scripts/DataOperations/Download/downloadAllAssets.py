#
# Download All Assets
# Script to download everything is in automatic download.
#

import asyncio

import nfpy.Downloader as Dwn
import nfpy.IO as IO

__version__ = '0.7'
_TITLE_ = "<<< Update database script >>>"
__purpose__ = "Updates the time series according to the Downloads table"
__desc__ = """
The script uses the Downloads table to gather the required information for
updating the time series in the database. The following parameters can be
overridden by the user:
    - override date [bool]: with True overrides the default frequency of
        downloads that determines when a time series can be updated.
    - provider [str]: filter for the downloads relative to the given provider.
    - page [str]: filter for the downloads relative to the given page.
    - ticker [str]: filter for the downloads relative to the given ticker.
    - override automatic [bool]: with True allows to update the items marked as
        inactive not automatically downloaded.
    - save [bool]: with False does not save the results in the database.
"""

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    dwnf = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    do_save, override_date, override_active = True, False, False
    provider, page, ticker = None, None, None

    give_p = inh.input('Do you want to specify parameters (default: No)?: ',
                       idesc='bool', default=False, optional=True)
    if give_p:
        override_date = inh.input("Override dates (default No)?: ",
                                  idesc='bool', default=False, optional=True)
        provider = inh.input("Download for a specific provider (default None)?: ",
                             idesc='str', default=None, optional=True,
                             checker='provider')
        page = inh.input("Download for a specific page (default None)?: ",
                         idesc='str', default=None, optional=True)
        ticker = inh.input("Download for a specific ticker (default None)?: ",
                           idesc='str', default=None, optional=True)
        override_active = inh.input("Override automatic (default No)?: ",
                                    idesc='bool', default=False, optional=True)
        do_save = inh.input("Save to database (default Yes)?: ",
                            idesc='bool', default=True, optional=True)

    # loop = asyncio.new_event_loop()
    # loop.set_debug(True)
    # print('Loop started')

    # loop.run_until_complete(
    dwnf.run_download(do_save=do_save, override_date=override_date,
                      provider=provider, page=page, ticker=ticker,
                      override_active=override_active)
    # )

    # loop.stop()
    # loop.close()
    # print('Loop closed')

    print("All done!")
