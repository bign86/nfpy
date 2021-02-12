#
# Download All Assets
# Script to download everything is in automatic download.
#

import nfpy.Downloader as Dwn
import nfpy.IO as IO

__version__ = '0.5'
_TITLE_ = "<<< Update database script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    dwnf = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    do_save, override_date, override_active = True, False, False
    provider, page = None, None

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
        override_active = inh.input("Override automatic (default No)?: ",
                                    idesc='bool', default=False, optional=True)

    dwnf.run(do_save=do_save, override_date=override_date,
             provider=provider, page=page, override_active=override_active)

    print("All done!")
