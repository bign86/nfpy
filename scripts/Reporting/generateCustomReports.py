#
# Create custom report
# Run the report engine on custom reports defined on-the-fly
#

import argparse
import json
import os.path as path

from nfpy.Calendar import (get_calendar_glob)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Reporting import (get_re_glob, ReportData)
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

__version__ = '0.4'
_TITLE_ = "<<< Custom report generation script >>>"

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    conf = get_conf_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'input', type=str, help='Input file'
    )
    args = parser.parse_args()

    # Fields
    cols = qb.get_columns('Reports')

    try:
        fp = open(path.join(args.input), 'r')
    except RuntimeError as ex:
        Ut.print_exc(FileNotFoundError('File not found!'))
        raise ex

    json_file = json.load(fp)

    data = [json_file[f.field] for f in cols.values()]
    start = json_file['start']
    end = json_file['end']

    # Create ReportData object and run
    cal.initialize(end, start)
    get_re_glob().run_custom([ReportData(*data)])

    Ut.print_ok('All done!')
