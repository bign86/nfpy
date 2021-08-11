#
# Add new report
# Add a new report to the database
#

import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.Reporting as Re

__version__ = '0.4'
_TITLE_ = "<<< New report add script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()
    re = Re.get_re_glob()

    # Insert a new report name
    name = inh.input("Insert report name: ", idesc='str')
    while re.exists(name):
        name = inh.input("Already in use. Choose a new name: ", idesc='str')

    # Get report data
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
          f'active      = {"Yes" if active else "No"}\n' \
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
