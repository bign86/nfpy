#
# Download All Assets
# Script to download everything is in automatic download.
#

import argparse
# import asyncio

import nfpy.Downloader as Dwn
import nfpy.IO as IO
from nfpy.Tools import get_logger_glob

__version__ = '0.8'
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
    logger = get_logger_glob()
    logger.info(_TITLE_)

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--interactive', action='store_true',
                            help='use interactively')
        parser.add_argument('-d', '--override-date', action='store_true',
                            help='override date in DB')
        parser.add_argument('-p', '--provider', nargs='?',
                            help='set a provider')
        parser.add_argument('-g', '--page', nargs='?',
                            help='set a page')
        parser.add_argument('-t', '--ticker', nargs='?',
                            help='set a ticker')
        parser.add_argument('-a', '--override-active', action='store_true',
                            help='override <active> flag in DB')
        parser.add_argument('-s', '--no-save', action='store_false',
                            help='do not save in DB')
        args = parser.parse_args()

        if args.interactive is True:
            inh = IO.InputHandler()

            give_p = inh.input('Do you want to specify parameters (default: No)?: ',
                               idesc='bool', default=False, optional=True)
            if give_p:
                args.override_date = inh.input("Override dates (default No)?: ",
                                               idesc='bool', default=False, optional=True)
                args.provider = inh.input("Download for a specific provider (default None)?: ",
                                          idesc='str', default=None, optional=True,
                                          checker='provider')
                args.page = inh.input("Download for a specific page (default None)?: ",
                                      idesc='str', default=None, optional=True)
                args.ticker = inh.input("Download for a specific ticker (default None)?: ",
                                        idesc='str', default=None, optional=True)
                args.override_active = inh.input("Override automatic (default No)?: ",
                                                 idesc='bool', default=False, optional=True)
                args.no_save = inh.input("Save to database (default Yes)?: ",
                                         idesc='bool', default=True, optional=True)
    except RuntimeError as ex:
        logger.error(str(ex))
        raise ex

    dwnf = Dwn.get_dwnf_glob()

    # loop = asyncio.new_event_loop()
    # loop.set_debug(True)
    # print('Loop started')

    # loop.run_until_complete(
    dwnf.run_download(
        do_save=args.no_save,
        override_date=args.override_date,
        provider=args.provider,
        page=args.page,
        ticker=args.ticker,
        override_active=args.override_active
    )
    # )

    # loop.stop()
    # loop.close()
    # print('Loop closed')

    logger.info("All done!")
