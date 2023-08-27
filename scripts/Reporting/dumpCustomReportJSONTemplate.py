#
# Dump Custom Report JSON Template
# Dump an empty JSON to be filled for the generateCustomReport command.
#

import argparse
import json
import os

from nfpy.Calendar import today
from nfpy.IO import InputHandler
import nfpy.Reporting.Reports as Rep
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

__version__ = '0.2'
_TITLE_ = "<<< Dump Custom Report JSON Template script >>>"

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    working_folder = get_conf_glob().working_folder

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--interactive', action='store_true', help='use interactively'
    )
    parser.add_argument(
        '-p', '--path', type=str, dest='path_out', help='Output file path'
    )
    parser.add_argument(
        '-r', '--report', type=str, dest='report', help='Report class'
    )
    args = parser.parse_args()

    if args.interactive is True:
        inh = InputHandler()

        msg = 'Give a report class (default None): '
        report = inh.input(msg, idesc='str', optional=True, default=None)

        msg = f'Give an output folder\n(default {working_folder})\n'
        path = inh.input(
            msg, idesc='str', optional=True,
            default=working_folder
        )
        while not os.path.isdir(path):
            path = inh.input('Folder not found, retry: ', idesc='str')

    else:
        path = args.path_out if args.path_out else working_folder
        report = args.report if args.report else None

    if report is not None:
        rep = getattr(Rep, report)
        params = rep.DEFAULT_P
    else:
        params = {}
        report = 'report'

    # Fields
    j = {
        'start': '1900-01-01',
        'end': today(mode='str'),
        'id': 'name',
        'title': 'title',
        'description': 'description',
        'template': 'template',
        'report': report,
        'uids': [],
        'active': False,
        'parameters': params,
    }

    # Create JSON
    new_json = os.path.join(path, 'report_template.json')
    fp = open(new_json, 'w')
    json.dump(j, fp, indent=4)
    Ut.print_ok(f'Template JSON created in {new_json}', end='\n\n')

    Ut.print_ok('All done!')
