#
# Insert/Update Record script
# Insert/Update any database record, one at a time.
#

from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.4'
_TITLE_ = "<<< Record insert/update script >>>"
_DESC_ = """Manually modifies any single row in the database. The selection is done using all
table keys to ensure a single record is found. If the searched record is missing it will be add
to the table. DANGEROUS! USE AT YOUR OWN RISK!"""

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # get the table to update
    table = inh.input("Table to update: ", idesc='str')
    while not qb.exists_table(table):
        table = inh.input(f"Table {table} does not exists, try again: ", idesc='str')
    columns = qb.get_columns(table)

    # get the primary keys to use to select the record
    keys_data = list()
    keys = list()
    for k, c in columns.items():
        if not c.is_primary:
            continue
        col_type = DB.SQLITE2PY_CONVERSION[c.type]
        v = inh.input(f"Insert {c.field}: ", idesc=col_type)
        keys_data.append(v)
        keys.append(k)
    q = qb.select(table, keys=keys)
    actual = db.execute(q, tuple(keys_data)).fetchone()

    # If found, show the record as ask what to do with it
    if actual:
        # Load all data and show them
        fields = tuple(columns.keys())
        data = list((f, v) for f, v in zip(fields, actual))

        msg = f'Record found in the database! Available data:\n' \
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

                msg = f' - {col}: {actual[idx]} to: '
                col_type = DB.SQLITE2PY_CONVERSION[columns[col].type]
                value = inh.input(msg, idesc=col_type)

                upd_fields.append(col)
                upd_data.append(value)

            # If something has been changed, update the database
            if upd_fields:
                q = qb.update(table, keys=keys, fields=upd_fields)
                db.execute(q, tuple(upd_data + keys_data), commit=True)

    # If no entry is found we create one from scratch
    else:
        # Get the data for the missing fields
        for k, c in columns.items():
            if c.is_primary:
                continue
            col_type = DB.SQLITE2PY_CONVERSION[c.type]
            v = inh.input(
                f"Insert {c.field} ({c.type}): ",
                idesc=col_type, optional=not c.notnull
            )
            keys_data.append(v)
            keys.append(k)

        # Insert data in the table
        print(f"Performing the update...")
        q = qb.insert(table, ins_fields=keys)
        db.execute(q, tuple(keys_data), commit=True)

    Ut.print_ok('All done!')
