#
# Download All Assets
# Script to download everything is in automatic download.
#

from nfpy.Downloader.DownloadFactory import get_dwnf_glob
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.2'
_TITLE_ = "<<< Update database script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    dwnf = get_dwnf_glob()
    inh = InputHandler()

    do_save, override_date, override_active = True, False, False
    provider, page, uid = None, None, None

    give_p = inh.input('Do you want to specify parameters (default: No)?: ',
                       idesc='bool', default=False, optional=True)
    if give_p:
        override_date = inh.input("Override dates (default No)?: ",
                                  idesc='bool', default=False, optional=True)
        provider = inh.input("Download for a specific provider (default None)?: ",
                             idesc='str', default=None, optional=True)
        page = inh.input("Download for a specific page (default None)?: ",
                         idesc='str', default=None, optional=True)
        uid = inh.input("Download for a specific uid (default None)?: ",
                        idesc='str', default=None, optional=True)
        override_active = inh.input("Override automatic (default No)?: ",
                                    idesc='bool', default=False, optional=True)

    dwnf.bulk_download(do_save=do_save, override_date=override_date,
                       provider=provider, page=page, uid=uid,
                       override_active=override_active)

    print("All done!")
