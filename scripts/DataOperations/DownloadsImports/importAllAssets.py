#
# Import All Assets
# Script to import everything is in automatic import.
#

import argparse

import nfpy.Calendar as Cal
import nfpy.Downloader as Dwn
import nfpy.IO as IO
from nfpy.Tools import get_logger_glob

__version__ = '0.9'
_TITLE_ = "<<< Import into elaboration database script >>>"

if __name__ == '__main__':
    logger = get_logger_glob()
    logger.info(_TITLE_)

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--interactive', action='store_true',
                            help='use interactively')
        parser.add_argument('-p', '--provider', nargs='?',
                            help='set a provider')
        parser.add_argument('-t', '--item', nargs='?',
                            help='set an item')
        parser.add_argument('-u', '--uid', nargs='?',
                            help='set a uid')
        parser.add_argument('-a', '--override-active', action='store_true',
                            help='override <active> flag in DB')
        parser.add_argument('-c', '--no-incremental', action='store_false',
                            help='do not use incremental import')
        args = parser.parse_args()

        if args.interactive:
            inh = IO.InputHandler()

            give_p = inh.input(
                'Do you want to specify parameters (default No)?: ',
                idesc='bool', default=False, optional=True
            )
            if give_p:
                args.provider = inh.input(
                    "Import for a specific provider (default None)?: ",
                    idesc='str', default=None, optional=True
                )
                args.item = inh.input(
                    "Import for a specific item (default None)?: ",
                    idesc='str', default=None, optional=True
                )
                args.uid = inh.input(
                    "Import for a specific uid (default None)?: ",
                    idesc='str', default=None, optional=True
                )
                args.override_active = inh.input(
                    "Override automatic (default No)?: ",
                    idesc='bool', default=False, optional=True
                )
                args.no_incremental = inh.input(
                    "Do incremental import (default True)?: ",
                    idesc='bool', default=True, optional=True
                )
    except RuntimeError as ex:
        logger.error(str(ex))
        raise ex

    cal = Cal.get_calendar_glob()
    cal.initialize(
        Cal.last_business(),
        Cal.shift(Cal.last_business(mode='timestamp'), -2, 'B')
    )
    dwnf = Dwn.get_dwnf_glob()

    dwnf.run_import(provider=args.provider, item=args.item, uid=args.uid,
                    override_active=args.override_active,
                    incremental=args.no_incremental)

    logger.info("All done!")
