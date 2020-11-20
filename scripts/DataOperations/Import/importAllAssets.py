#
# Import All Assets
# Script to import everything is in automatic import.
#

from nfpy.Downloader.ImportFactory import get_impf_glob
from nfpy.Handlers.Calendar import get_calendar_glob, today, last_business
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.3.1'
_TITLE_ = "<<< Import into elaboration database script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    cal.initialize(today(), last_business())

    impf = get_impf_glob()
    inh = InputHandler()

    override_active = False
    provider, page, uid = None, None, None

    give_p = inh.input('Do you want to specify parameters (default: No)?: ',
                       idesc='bool', default=False, optional=True)
    if give_p:
        provider = inh.input("Import for a specific provider (default None)?: ",
                             idesc='str', default=None, optional=True)
        page = inh.input("Import for a specific page (default None)?: ",
                         idesc='str', default=None, optional=True)
        uid = inh.input("Import for a specific uid (default None)?: ",
                        idesc='str', default=None, optional=True)

        override_active = inh.input("Override automatic (default No)?: ",
                                    idesc='bool', default=False, optional=True)

    impf.bulk_import(provider=provider, page=page,
                     uid=uid, override_active=override_active)

    print("All done!")
