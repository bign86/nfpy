#
# Create Portfolio Script
# Script to create a new portfolio.
#
# KNOWN BUGS:
#  - the datetime conversion in input inserts a datetime (not a date) in the DB

from nfpy.Assets.Portfolio import Portfolio
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.3'
_TITLE_ = "<<< Create portfolio script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Variable
    base_table = Portfolio._BASE_TABLE
    cnst_table = Portfolio._CONSTITUENTS_TABLE
    base_cols = qb.get_columns(base_table)
    cnst_cols = qb.get_columns(cnst_table)

    # Choose a uid and check for existence
    uid = inh.input("Give a uid for the new portfolio: ", idesc='uid')
    q_ptf = qb.select("Assets", keys=('uid',))
    l = db.execute(q_ptf, (uid,)).fetchall()
    if l:
        raise ValueError("The selected uid already exists!")

    # Position dictionary
    pos_dict = {'ptf_uid': uid, 'asset_uid': uid, 'type': 'Currency', 'alp': 1.}

    # Fill in data
    ptf_data = []
    for n, c in base_cols.items():
        if c.field == 'uid':
            ptf_data.append(uid)
            continue
        col_type = DB.SQLITE2PY_CONVERSION[c.type]
        optional = False if c.notnull else True
        v = inh.input(f"Insert {c.field} ({c.type}): ",
                      idesc=col_type, optional=optional)
        if c.field == 'currency':
            pos_dict['pos_uid'] = v
            pos_dict['currency'] = v
        elif c.field == 'inception_date':
            pos_dict['date'] = v
        ptf_data.append(v)

    # Create the position
    msg = 'A cash position in the base currency will be created\nInsert the cash amount: '
    pos_dict['quantity'] = inh.input(msg, idesc='float')

    # Fill in position
    for n, c in cnst_cols.items():
        if c.field not in pos_dict:
            col_type = DB.SQLITE2PY_CONVERSION[c.type]
            optional = False if c.notnull else True
            v = inh.input(f"Insert {c.field} ({c.type}): ",
                          idesc=col_type, optional=optional)
            pos_dict[c.field] = v

    # Write to database
    q_ptf = qb.insert(base_table)
    q_pos = qb.insert(cnst_table)
    db.execute(q_ptf, tuple(ptf_data))
    db.execute(q_pos, tuple(pos_dict[c.field] for c in cnst_cols.values()))

    print("All done!")
