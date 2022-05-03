#
# Update report target items
# Add/remove uids to the report
#

from tabulate import tabulate

import nfpy.Assets as As
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Update report target items script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = Cal.get_calendar_glob()
    cal.initialize(Cal.today(), Cal.last_business())

    af = As.get_af_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Choose a report to modify
    prk = tuple(qb.get_keys('Reports'))
    reports = db.execute(
        qb.selectall('Reports', fields=prk)
    ).fetchall()

    msg = f'Choose a report to update:\n' \
          f'{tabulate(reports, headers=prk, showindex=True)}\n' \
          f'Give an report index: '
    idx = inh.input(msg, idesc='int')

    # Fetch data
    uids = db.execute(
        qb.select(
            'Reports',
            fields=('uids',),
            keys=prk
        ),
        reports[idx]
    ).fetchall()[0][0]
    msg = f'Current uids are:\n'
    for u in uids:
        msg += f'  > {u} ({af.get_type(u)})\n'
    print(msg)

    # Add uids
    to_add = inh.input('List uids to add, comma separated: ',
                       is_list=True, default=[])

    # Check for associated equity/companies
    for u in to_add:
        v = af.get(u)
        if (v.type == 'Equity') \
                and (v.company not in to_add) \
                and (v.company not in uids):
            msg = f'You added {u} (Equity). Do you also want to add the ' \
                  f'company {v.company}? (Default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_add.append(v.company)
        elif (v.type == 'Company') \
                and (v.equity not in to_add) \
                and (v.equity not in uids):
            msg = f'You added {u} (Company). Do you also want to add the ' \
                  f'equity {v.equity}? (Default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_add.append(v.equity)

    # Remove uids
    to_rem = inh.input('List uids to remove, comma separated: ',
                       is_list=True, default=[])

    # Check for associated equity/companies
    for u in to_rem:
        v = af.get(u)
        if (v.type == 'Equity') \
                and ((v.company in to_add) or (v.company in uids)):
            msg = f'You removed {u} (Equity). Do you also want to remove ' \
                  f'the company {v.company}? (Default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_rem.append(v.company)
        elif (v.type == 'Company') \
                and ((v.equity in to_add) or (v.equity in uids)):
            msg = f'You removed {u} (Company). Do you also want to remove ' \
                  f'the equity {v.equity}? (Default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_rem.append(v.equity)

    # Update list
    uids = list((set(uids) - set(to_rem)) | set(to_add))

    if inh.input('Proceed with the changes (Default No)?: ',
                 idesc='bool', default=False):
        db.execute(
            qb.update(
                'Reports',
                fields=('uids',),
                keys=prk
            ),
            (uids, reports[idx][0])
        )

    print('All done!')
