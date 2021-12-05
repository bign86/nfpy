#
# Add new report
# Add a new report to the database
#

import json

from nfpy.Tools import get_conf_glob
import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.Reporting as Re

__version__ = '0.4'
_TITLE_ = "<<< New report add script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    conf = get_conf_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()
    re = Re.get_re_glob()

    # Insert a new report name

    # Get report data
    msg = f'Give a JSON file with data. Path is assumed relative to the working\n' \
          f'folder {conf.working_folder}.\n' \
          f'If not found the file is searched assuming an absolute path.\n' \
          f'The JSON shall contain the following fields:\n' \
          f' - name: name given to report, must be unique\n' \
          f' - description: text\n - template: html template file\n' \
          f' - report: name of report class\n - uids: list of uids\n' \
          f' - active: 1 if to generate automatically, 0 otherwise\n' \
          f' - parameters: dictionary of required parameters\n\n' \
          f'Insert nothing for manual input of the required data.\n'
    file_name = inh.input(msg, optional=True)
    if file_name:
        data = json.load(open(file_name, 'r'))

        name = data['name']
        if re.exists(name):
            raise ValueError("Unique report name already in use.")
        desc = data['description']
        report = data['report']
        template = data['template']
        uids = data['uids']
        active = data['active']
        parameters = data['parameters']
    else:
        name = inh.input("Insert report name: ", idesc='str')
        if re.exists(name):
            raise ValueError("Unique report name already in use.")

        desc = inh.input("Insert a description: ", optional=True)
        report = inh.input("Insert a type: ")
        while report not in re.get_report_types():
            report = inh.input("Wrong report type. Insert a new one: ")
        template = inh.input("Insert a template: ")
        uids = inh.input("Insert a list of target uids: ", is_list=True)
        active = inh.input("Set the model as automatic: ", idesc='bool')
        parameters = re.get_report_obj(report).DEFAULT_P

    # Print out and confirmation
    msg = f'\nThe following will be created:\n' \
          f'name        = {name}\n' \
          f'description = {desc}\n' \
          f'report      = {report}\n' \
          f'template    = {template}\n' \
          f'#uids       = {len(uids)}\n' \
          f'active      = {"Yes" if bool(active) else "No"}\n' \
          f'parameters  = {parameters}\n' \
          f'\nSave the current report?: '
    if inh.input(msg, idesc='bool'):
        db.execute(
            qb.insert(
                'Reports',
                fields=('name', 'description', 'report',
                        'template', 'uids', 'parameters', 'active')
            ),
            (name, desc, report, template, uids, parameters, active),
            commit=True
        )
        print('Saved!')

    print('All done!')
