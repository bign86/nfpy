#
# Download Single Asset
# Script to download from internet a single page
#

from tabulate import tabulate

from nfpy.DB import (get_db_glob, get_qb_glob)
from nfpy.Downloader.DownloadFactory import get_dwnf_glob
from nfpy.Handlers.Calendar import today
from nfpy.Handlers.Inputs import InputHandler
from nfpy.Tools.Utilities import list_to_dict

__version__ = '0.3'
_TITLE_ = "<<< Download single asset script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    f = get_dwnf_glob()
    qb = get_qb_glob()
    db = get_db_glob()
    inh = InputHandler()

    uid = inh.input("Give a UID to download for: ", idesc='str')
    fields, data = f.downloads_by_uid(uid=uid, active=False)
    if not data:
        raise ValueError('Supplied UID does not exist! Please give a valid one.')

    tab = tabulate(data, headers=fields, showindex=True)
    print(tab, end='\n\n')
    choice = inh.input('Index: ', idesc='int')
    while choice >= len(data) or choice < 0:
        print('*** Invalid index! ***')
        choice = inh.input('Index: ', idesc='int')

    dwn = data[choice]
    p = f.create_page_obj(dwn[1], dwn[2])
    num_params = f.print_parameters(p)

    kwargs = {}
    if num_params > 0:
        msg = "Type the additional parameters as a comma separated list of key, value pairs:\n"
        pin = inh.input(msg, idesc='str', is_list=True, default=[])
        kwargs = list_to_dict(pin)

    p = f.initialize(p, dwn[3], dwn[4], **kwargs)
    p.fetch()
    p.printout()

    save = inh.input('\nSave the results to database?', idesc='bool', default=False)
    if save:
        p.save()
        # TODO: write a logic inside the download factory to get rid of this
        #       external logic here. We don't want to deal with QueryBuilder and
        #       database directly but hand off to the DownloadFactory
        data_upd = (today(), uid, dwn[1], dwn[2])
        q_upd = qb.merge('Downloads', fields=['last_update'])
        db.execute(q_upd, data_upd, commit=True)

    print('fine')
