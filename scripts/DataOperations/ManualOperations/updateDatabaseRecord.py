#
# Insert/Update Record script
# Insert/Update any database record.
#

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.3'
_TITLE_ = "<<< Record insert/update script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # get the table to update
    table = inh.input("Table to update: ", idesc='str')
    if not qb.exists_table(table):
        raise ValueError(f"Table {table} does not exists in the database")
    columns = qb.get_columns(table)

    # get the primary keys to use to select the record
    d_keys = list()
    keys = list()
    for k, c in columns.items():
        if not c.is_primary:
            continue
        col_type = IO.SQLITE2PY_CONVERSION[c.type]
        v = inh.input(f"Insert {c.field}: ", idesc=col_type)
        d_keys.append(v)
        keys.append(k)
    q = qb.select(table, keys=keys)
    actual = db.execute(q, tuple(d_keys)).fetchone()

    # give new values
    d, f = [], []
    for k, c in columns.items():
        if c.is_primary:
            continue
        col_type = IO.SQLITE2PY_CONVERSION[c.type]
        v = inh.input(f"Insert {c.field} ({c.type}): ", idesc=col_type)
        if v is not None:
            d.append(v)
            f.append(c.field)

    if actual:
        # update the database
        q = qb.update(table, fields=f)
        db.execute(q, tuple(d + d_keys), commit=True)
    else:
        # insert
        d.extend(d_keys)
        f.extend(keys)
        q = qb.insert(table, fields=f)
        db.execute(q, tuple(d), commit=True)

    print("All done!")
