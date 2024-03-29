#
# Archive report
# Archive old reports
#

import os
from shutil import make_archive, rmtree
from datetime import timedelta, datetime

from nfpy.Calendar import today
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

__version__ = '0.3'
_TITLE_ = "<<< Report archiving script >>>"


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    conf = get_conf_glob()
    src = conf.report_path
    dest = conf.report_arch_path
    zip_fmt = conf.archive_format
    retention = conf.report_retention

    t0 = today(mode='datetime')
    start = t0 - timedelta(days=retention)
    print(f'Retention of {retention} days.\n'
          f'Will delete folders before {start.strftime("%Y-%m-%d")}')

    # If destination does not exist, create it
    if not os.path.isdir(dest):
        Ut.print_wrn(Warning('Archive destination not found, creating new one'))
        os.mkdir(dest)
        Ut.print_ok(f'Created folder {dest}')

    # Extract all folders
    folders = [(f.path, f.name) for f in os.scandir(src) if f.is_dir()]

    # Archive and delete archived trees
    os.chdir(dest)
    archived = 0
    for path, name in folders:
        date_str = name.split('_')[1]
        date = datetime.strptime(date_str, '%Y%m%d')

        if date < start:
            print(f' - Archiving {name}', end='')
            try:
                make_archive(name, zip_fmt, root_dir=path)
            except Exception as ex:
                Ut.print_exc(ex)
                continue
            else:
                rmtree(path)
                archived += 1
                print('  -> Cleaned')

    Ut.print_ok(f'Archived {archived} of {len(folders)} reports', end='\n\n')

    Ut.print_ok('All done!')
