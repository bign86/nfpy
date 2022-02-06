#
# Dump report configuration
# Create a JSON configuration file from a database report entry
#

import json
import os
from pandas import DateOffset
from tabulate import tabulate

import nfpy.Calendar as Cal
from nfpy.Tools import get_conf_glob
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Dump report configuration script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    conf = get_conf_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Get reports
    msg = "Give a list of report ids (press Enter to see existing reports): "
    rep_ids = inh.input(msg, default=[], is_list=True)
    if not rep_ids:
        fields = ('id', 'title', 'report', 'active')
        q = f"select {', '.join(fields)} from Reports"
        res = db.execute(q).fetchall()

        msg = f'\nAvailable reports:\n' \
              f'{tabulate(res, headers=fields, showindex=True)}\n' \
              f'Give a report index: '
        idx = inh.input(msg, idesc='int', is_list=True)
        while min(idx) < 0 or max(idx) >= len(res):
            idx = inh.input('Not possible. Given another index: ', idesc='int')
        rep_ids = [res[i][0] for i in idx]

    q = f"select * from Reports where id = ?"
    cols = qb.get_fields('Reports')
    today = Cal.today(mode='timestamp')
    start = (today - DateOffset(months=120)).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    for rep_id in rep_ids:
        fp = open(
            os.path.join(conf.working_folder, rep_id+'.json'),
            'w'
        )
        res = db.execute(q, (rep_id,)).fetchone()
        data = dict((k, v) for k, v in zip(cols, res))
        data['start'] = start
        data['end'] = end
        json.dump(data, fp)
        fp.close()

    print('All done!')
