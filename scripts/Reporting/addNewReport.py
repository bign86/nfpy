#
# Add new report
# Create a new report into the database
#

import json
import os.path as path

from nfpy.Tools import get_conf_glob
import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.Reporting as Re
from nfpy.Tools import Utilities as Ut

__version__ = '0.5'
_TITLE_ = "<<< New report add script >>>"

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    conf = get_conf_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()
    re = Re.get_re_glob()

    # Insert a new report name

    # Get report data
    msg = f'Give the path to a JSON file with data.\n' \
          f'The JSON shall contain the following fields:\n' \
          f' - name: name given to report, must be unique\n' \
          f' - description: text\n - template: html template file\n' \
          f' - report: name of report class\n - uids: list of uids\n' \
          f' - active: 1 if to generate automatically, 0 otherwise\n' \
          f' - parameters: dictionary of required parameters\n\n' \
          f'Insert nothing for manual input of the required data.\n'
    file_name = inh.input(msg, optional=True)
    while (file_name is not None) and (not path.isfile(file_name)):
        file_name = inh.input('File not found, retry: ', optional=True, default=None)

    if file_name:
        try:
            fp = open(file_name, 'r')
        except RuntimeError as ex:
            Ut.print_exc(FileNotFoundError('File not found!'))
            raise ex
        data = json.load(fp)

        _id = data['id']
        if re.exists(_id):
            raise ValueError("Unique report name already in use.")
        title = data['title']
        desc = data['description']
        report = data['report']
        template = data['template']
        uids = data['uids']
        active = data['active']
        parameters = data['parameters']
    else:
        _id = inh.input("Insert report id: ", idesc='str')
        while re.exists(_id):
            _id = inh.input("Id already in use, retry: ", idesc='str')

        title = inh.input("Insert a title: ")
        desc = inh.input("Insert a description: ", optional=True)
        report = inh.input("Insert the report object: ")
        while not re.report_obj_exist(report):
            report = inh.input("Wrong report object. Insert a new one: ")
        template = inh.input("Insert a template: ")
        uids = inh.input("Insert a list of target uids: ", is_list=True)
        active = inh.input("Set the model as automatic: ", idesc='bool')
        parameters = re.get_report_obj(report).DEFAULT_P

    # Print out and confirmation
    msg = f'\nThe following will be created:\n' \
          f'id          = {_id}\n' \
          f'title       = {title}\n' \
          f'description = {desc}\n' \
          f'report      = {report}\n' \
          f'template    = {template}\n' \
          f'# uids      = {len(uids)}\n' \
          f'active      = {"Yes" if bool(active) else "No"}\n' \
          f'parameters  = {parameters}\n' \
          f'\nSave the current report?: '
    if inh.input(msg, idesc='bool'):
        db.execute(
            qb.insert(
                ins_table='Reports',
                ins_fields=('id', 'title', 'description', 'report',
                            'template', 'uids', 'parameters', 'active'),
                table='Reports'
            ),
            (_id, title, desc, report, template, uids, parameters, active),
            commit=True
        )
        Ut.print_ok('Saved!')

    Ut.print_ok('All done!')
