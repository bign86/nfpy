#
# Import All Assets
# Script to import everything is in automatic import.
#

from nfpy.Calendar import (get_calendar_glob, today, last_business)
import nfpy.Downloader as Dwn
import nfpy.IO as IO

__version__ = '0.5'
_TITLE_ = "<<< Import into elaboration database script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    cal.initialize(today(), last_business())
    impf = Dwn.get_impf_glob()
    inh = IO.InputHandler()

    override_active, incremental = False, False
    provider, item, uid = None, None, None

    give_p = inh.input('Do you want to specify parameters (default: No)?: ',
                       idesc='bool', default=False, optional=True)
    if give_p:
        provider = inh.input("Import for a specific provider (default None)?: ",
                             idesc='str', default=None, optional=True)
        item = inh.input("Import for a specific item (default None)?: ",
                         idesc='str', default=None, optional=True)
        uid = inh.input("Import for a specific uid (default None)?: ",
                        idesc='str', default=None, optional=True)
        override_active = inh.input("Override automatic (default No)?: ",
                                    idesc='bool', default=False, optional=True)
        incremental = inh.input("Do incremental import (default False)?: ",
                                idesc='bool', default=False, optional=True)

    impf.bulk_import(provider=provider, item=item, uid=uid,
                     override_active=override_active, incremental=incremental)

    print("All done!")
