#
# Create custom report
# Run the report engine on custom reports defined on-the-fly
#

import json
import os.path as path

from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Reporting import (get_re_glob, ReportData)
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

__version__ = '0.2'
_TITLE_ = "<<< Custom report generation script >>>"

# _FIELDS = (
#     ('id', 'custom', 'str'),
#     ('title', 'custom', 'str'),
#     ('description', '', 'str'),
#     ('report', None, 'str'),
#     ('template', None, 'str'),
#     ('uids', '[]', 'json'),
#     ('parameters', '{}', 'json'),
#     ('active', False, 'bool')
# )

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    conf = get_conf_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Fields
    cols = qb.get_columns('Reports')

    # Define reports
    msg = f'Give a JSON file with data. Path is assumed relative to the working\n' \
          f'folder {conf.working_folder}.\n' \
          f'If not found the file is searched assuming an absolute path.\n' \
          f'The JSON shall contain the following fields:\n' \
          f' - start: calendar start date\n - end: calendar end date\n' \
          f' - id: name given to report\n' \
          f' - title: title of the report\n' \
          f' - description: text\n - template: html template file\n' \
          f' - report: name of report class\n - uids: list of uids\n' \
          f' - active: 1 if to generate automatically, 0 otherwise\n' \
          f' - parameters: dictionary of required parameters\n\n' \
          f'Insert nothing for manual input of the required data.\n'
    file_name = inh.input(msg, optional=True)
    if file_name:
        try:
            fp = open(
                path.join(conf.working_folder, file_name),
                'r'
            )
        except RuntimeError:
            try:
                fp = open(file_name, 'r')
            except RuntimeError as ex:
                Ut.print_exc(FileNotFoundError('File not found!'))
                raise ex
        json_file = json.load(fp)

        data = [json_file[f.field] for f in cols.values()]
        start = json_file['start']
        end = json_file['end']
    else:
        start = inh.input('Insert a start date: ', idesc='timestamp')
        end = inh.input('Insert an end date: ', idesc='timestamp',
                        default=today(mode='timestamp'))
        data = [
            inh.input(f'Insert {f.field}: ', idesc=f.type)
            for f in cols.values()
        ]
        print()

    # Create ReportData object and run
    cal.initialize(end, start)
    get_re_glob().run_custom([ReportData(*data)])

    print('All done!')
