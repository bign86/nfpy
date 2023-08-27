#
# Update Financial Item script
# Adds or updates a financial item in the elaboration database.
#

from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.4'
_TITLE_ = "<<< Financial item creation script >>>"
_DESC_ = """Updates a financial item in the elaboration engine or registers a new UID if not found."""

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Take the uid and search for an existing entry
    uid = inh.input("Give a uid to register: ", idesc='str')
    q = qb.select("Assets", keys=('uid',))
    l = db.execute(q, (uid,)).fetchone()

    # If an entry is found we must decide what do with it
    if l:
        # Load all data and show them
        columns = qb.get_columns(l[1])
        fields = tuple(columns.keys())
        q = qb.select(l[1], keys=('uid',))
        asset = db.execute(q, (uid,)).fetchone()
        data = list((f, v) for f, v in zip(fields, asset))

        msg = f'Record found in the database!\n' \
              f'\ttype\t\t\t{l[1]}\n' \
              f'\tdescription:\t{l[2]}\n' \
              f'Available data:\n' \
              f'{tabulate(data, headers=("field", "value"), showindex=True)}\n' \
              f'Do you want to update it? (default False): '

        # We can quickly exit if we do not want to modify it
        if not inh.input(msg, idesc='bool', default=False):
            print("Exiting now!")
            Ut.print_ok('All done!')
            exit()

        # If we want to modify it, take a list of what to change
        else:
            msg = f'\nGive a comma separated list of the indices of the fields to change:\n'
            idx_list = inh.input(msg, idesc='int', optional=True, is_list=True)

            upd_fields = []
            upd_data = []
            for idx in idx_list:
                col = fields[idx]

                msg = f' - {col}: {asset[idx]} to: '
                col_type = DB.SQLITE2PY_CONVERSION[columns[col].type]
                value = inh.input(msg, idesc=col_type)

                upd_fields.append(col)
                upd_data.append(value)

            # If something has been changed, update the database
            if upd_fields:
                q = qb.update(l[1], keys=('uid',), fields=upd_fields)
                db.execute(q, tuple(upd_data + [uid]), commit=True)

    # If no entry is found we create one from scratch
    else:
        # Get the asset_type and related table
        asset_type = inh.input("Insert asset_type: ", idesc='str')
        asset_obj = Ut.import_symbol(
            '.'.join(['nfpy.Assets', asset_type, asset_type])
        )
        table = asset_obj._BASE_TABLE

        # Fill in all data
        print(f"Will update table {table}")
        columns = qb.get_columns(table)

        q_fields = []
        q_data = []
        for n, c in columns.items():
            if c.field == 'uid':
                q_fields.append('uid')
                q_data.append(uid)
                continue
            col_type = DB.SQLITE2PY_CONVERSION[c.type]
            mandatory = c.notnull or c.is_primary
            v = inh.input(
                f"Insert {c.field} ({c.type}): ",
                idesc=col_type, optional=not mandatory
            )
            q_fields.append(c.field)
            q_data.append(v)

        # Insert data in the table
        print(f"Performing the update...")
        q = qb.insert(table, ins_fields=q_fields)
        db.execute(q, tuple(q_data))

    Ut.print_ok('All done!')
