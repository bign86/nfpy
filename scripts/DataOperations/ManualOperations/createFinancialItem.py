#
# Create Financial Item script
# Create a new financial item in the database.
#

from nfpy.DB import (get_db_glob, get_qb_glob)
from nfpy.Tools.Utilities import import_symbol
from nfpy.Handlers.Inputs import InputHandler, SQLITE2PY_CONVERSION

__version__ = '0.2'
_TITLE_ = "<<< Financial item creation script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    inh = InputHandler()

    # Register in the AssetInfo table
    uid = inh.input("Give a uid to register: ", idesc='uid')

    q = qb.select("Assets", keys=('uid',))
    l = db.execute(q, (uid,)).fetchall()
    if l:
        raise ValueError("The selected uid already exists!")
    asset_type = inh.input("Insert asset_type: ", idesc='str')

    # Register in the specific table
    # asset_obj = import_class(asset_type, mod='nfpy.Assets.' + asset_type)
    asset_obj = import_symbol('.'.join(['nfpy.Assets', asset_type, asset_type]))
    table = asset_obj._BASE_TABLE
    print("Updating table {}".format(table))
    if not qb.exists_table(table):
        raise ValueError("Table {} does not exists in the database".format(table))

    # Fill in data
    columns = qb.get_columns(table)
    d = list()
    for n, c in columns.items():
        if c.field == 'uid':
            d.append(uid)
            continue
        col_type = SQLITE2PY_CONVERSION[c.type]
        v = inh.input("Insert {} ({}): ".format(c.field, c.type), idesc=col_type)
        d.append(v)

    q = qb.insert(table)
    db.execute(q, tuple(d))

    print("All done!")
