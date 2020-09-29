#
# Create Portfolio Script
# Script to create a new portfolio.
#

from nfpy.Assets.Portfolio import Portfolio
from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Handlers.Calendar import date_2_datetime
from nfpy.Handlers.Inputs import InputHandler, SQLITE2PY_CONVERSION

__version__ = '0.1'
_TITLE_ = "<<< Create portfolio script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    inh = InputHandler()

    # Variable
    base_table = Portfolio._BASE_TABLE
    cnst_table = Portfolio._CONSTITUENTS_TABLE
    base_cols = qb.get_columns(base_table)
    cnst_cols = qb.get_columns(cnst_table)
    base_currency = None
    date = None

    # Choose a uid and check for existence
    uid = inh.input("Give a uid for the new portfolio: ", idesc='uid')
    q_ptf = qb.select("Assets", keys=('uid',))
    l = db.execute(q_ptf, (uid,)).fetchall()
    if l:
        raise ValueError("The selected uid already exists!")

    # Register in the specific table
    print("Updating table {}".format(base_table))
    if not qb.exists_table(base_table):
        raise ValueError("Table {} does not exists in the database".format(base_table))

    # Fill in data
    ptf_data = list()
    for n, c in base_cols.items():
        if c.field == 'uid':
            ptf_data.append(uid)
            continue
        col_type = SQLITE2PY_CONVERSION[c.type]
        v = inh.input("Insert {} ({}): ".format(c.field, c.type), idesc=col_type)
        if c.field == 'base_currency':
            base_currency = v
        ptf_data.append(v)

    # Create the position
    msg = 'A cash position in the base currency will be created\nInsert the cash amount: '
    amount = inh.input(msg, idesc='float')
    date = inh.input("Insert a creation date (default today): ", idesc='timestamp')
    date = date_2_datetime(date)

    # Fill in position
    pos_data = list()
    pos_dict = {'ptf_uid': uid, 'date': date, 'pos_uid': base_currency,
                'asset_uid': uid, 'type': 'Currency', 'currency': base_currency,
                'quantity': amount, 'alp': 1.}
    for n, c in cnst_cols.items():
        if c.field in pos_dict:
            pos_data.append(pos_dict[c.field])
            continue
        col_type = SQLITE2PY_CONVERSION[c.type]
        v = inh.input("Insert {} ({}): ".format(c.field, c.type), idesc=col_type)
        if c.field == 'base_currency':
            base_currency = v
        pos_data.append(v)

    # Write to database
    q_ptf = qb.insert(base_table)
    q_pos = qb.insert(cnst_table)
    db.execute(q_ptf, tuple(ptf_data))
    db.execute(q_pos, tuple(pos_data))

    print("All done!")
