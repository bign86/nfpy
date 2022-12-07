#
# Create JSON for custom report
# Create an empty JSON to be used with the generateCustomReport command.
#

import argparse
import json
import os.path as path

from nfpy.Calendar import today
from nfpy.Tools import get_conf_glob
import nfpy.Reporting.Reports as Rep

__version__ = '0.1'
_TITLE_ = "<<< Custom report JSON generation script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    conf = get_conf_glob()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--path', type=str, dest='path_out', help='Output file path'
    )
    parser.add_argument(
        '-r', '--report', type=str, dest='report', help='Report class'
    )
    args = parser.parse_args()

    if args.report:
        rep = getattr(Rep, args.report)
        params = rep.DEFAULT_P
        report = args.report
    else:
        params = {}
        report = 'report'

    if not args.path_out:
        args.path_out = conf.working_folder

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
    new_json = path.join(args.path_out, 'new_json.json')
    fp = open(new_json, 'w')
    json.dump(j, fp, indent=4)
    print(f'JSON created in {new_json}')

    print('All done!')
