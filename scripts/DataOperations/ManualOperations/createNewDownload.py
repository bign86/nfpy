#
# Create New Download script
# Register a new financial item in the database.
#

from nfpy.DB.DB import get_db_glob
from nfpy.Downloader.DownloadFactory import get_dwnf_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Tools.Utilities import import_symbol
from nfpy.Handlers.Inputs import InputHandler, SQLITE2PY_CONVERSION

__version__ = '0.2'
_TITLE_ = "<<< Create new download script >>>"


def update_table(_table: str, _data: dict) -> tuple:
    _cols = qb.get_columns(_table)
    _uid = None
    _opt = False
    _d = list()
    for _n, _c in _cols.items():
        if _c.field in _data:
            _d.append(_data[_c.field])
            continue
        _col_type = SQLITE2PY_CONVERSION[_c.type]
        _check = None
        if _c.field == 'currency':
            _check = 'currency'
        elif _c.field == 'isin':
            _check = 'isin'
        elif _c.field == 'last_update':
            _opt = True
        _v = inh.input("Insert {} ({}): ".format(_c.field, _c.type),
                       idesc=_col_type, checker=_check, optional=_opt)
        _d.append(_v)
        _data[_c.field] = _v

    _q = qb.insert(_table)
    return _data, {_table: (_q, _d)}


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    dwn = get_dwnf_glob()
    inh = InputHandler()

    data = dict()
    queries = dict()

    # DOWNLOADS
    # Add ticker to Download table
    data['ticker'] = inh.input("Give a downloading ticker to add: ", idesc='str')
    data['provider'] = inh.input("Give the provider: ", idesc='str')
    if not dwn.provider_exists(data['provider']):
        raise ValueError('The provider {} does not exist'.format(data['provider']))
    data['page'] = inh.input("Give the download page: ", idesc='str')
    if not dwn.page_exists(data['provider'], data['page']):
        raise ValueError('The page {} does not exist in this provider'.format(data['page']))

    add = inh.input("Add to download database?: ", idesc='bool')
    if add:
        # Check whether the combination uid, provider, page exists
        q = qb.select('Downloads', keys=('ticker', 'provider', 'page'))
        res = db.execute(q, (data['ticker'], data['provider'], data['page'])).fetchall()
        if res:
            raise ValueError("The selected combination already exists in Downloads!")

        # Update table
        data, qr = update_table('Downloads', data)
        queries.update(qr)
        if data['uid'] is None:
            raise ValueError("No uid inserted... That's weird!")

    # IMPORTS
    # Add to Imports?
    add = inh.input("Add to imports?: ", idesc='bool')
    if add:
        # Check if combination exists in Imports
        q = qb.select('Imports', keys=('ticker', 'provider', 'page'))
        res = db.execute(q, (data['ticker'], data['provider'], data['page'])).fetchall()
        if res:
            raise ValueError("The selected combination already exists in Imports!")

        data, qr = update_table('Imports', data)
        queries.update(qr)

    # ELABORATION
    # Add to elaboration database?
    add = inh.input("Add to elaboration database?: ", idesc='bool')
    if add:
        # Check whether the uid already exists
        q = qb.select('Assets', keys=('uid',))
        res = db.execute(q, (data['uid'],)).fetchall()
        if res:
            raise ValueError("The selected combination already exists in Downloads!")

        # Find the right table
        asset_type = inh.input("Insert asset_type: ", idesc='str')
        asset_obj = import_symbol('.'.join(['nfpy.Assets', asset_type, asset_type]))
        table = asset_obj._BASE_TABLE
        print("Updating table {}".format(table))
        if not qb.exists_table(table):
            raise ValueError("Table {} does not exists in the database".format(table))

        # Update the table
        data, qr = update_table(table, data)
        queries.update(qr)

    # Final check
    print('')
    for k, v in queries.items():
        print('Table: {}'.format(k))
        print('Params: {}'.format(', '.join(map(str, v[1]))), end='\n\n')

    # Final insert
    add = inh.input('Do you want to proceed?: ', idesc='bool')
    if add:
        for t in queries.values():
            query, data = t
            db.execute(query, data)

    print("All done!")
