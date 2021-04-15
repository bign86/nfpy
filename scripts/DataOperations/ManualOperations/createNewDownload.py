#
# Create New Download script
# Register a new financial item in the database.
#

import nfpy.Assets as As
import nfpy.Downloader as Dwn
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.5'
_TITLE_ = "<<< Create new download script >>>"


def columns_data(_table: str, _data: dict) -> tuple:
    _cols = qb.get_columns(_table)
    _d = list()
    for _n, _c in _cols.items():
        if _n in _data:
            _d.append(_data[_n])
            continue
        _col_type = IO.SQLITE2PY_CONVERSION[_c.type]
        _opt = False
        _check = None
        if _n == 'currency':
            _check = 'currency'
        elif _n == 'isin':
            _check = 'isin'
        elif _n == 'last_update':
            _opt = True
        _v = inh.input("Insert {} ({}): ".format(_n, _c.type),
                       idesc=_col_type, checker=_check, optional=_opt)
        _d.append(_v)

    return tuple(_d)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = As.get_af_glob()
    db = IO.get_db_glob()
    qb = IO.get_qb_glob()
    dwn = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    # Variables
    skip_elaboration = False
    queries, data = dict(), dict()

    # Choose a UID
    uid = inh.input('Give a UID: ', idesc='str')
    if af.exists(uid):
        skip_elaboration = True
        a_type = af.get_type(uid)
        print("UID has been found in the database:\n{} {}"
              .format(a_type, uid), end='\n\n')
    else:
        a_type = inh.input("Insert asset_type: ", idesc='str')
        a_obj = Ut.import_symbol('.'.join(['nfpy.Assets', a_type, a_type]))
        table = a_obj._BASE_TABLE
        asset_data = columns_data(table, {'uid': uid})
        queries[table] = (qb.insert(table), (asset_data,))

    # DOWNLOADS
    dwn_data = []
    dwn_keys = ('provider', 'page', 'ticker')
    while inh.input("Add new download?: ", idesc='bool', default=False):
        provider = inh.input("Give the provider: ", idesc='str',
                             checker='provider')

        page = inh.input("Give the download page: ", idesc='str')
        if not dwn.page_exists(provider, page):
            print('Page not recognized for this provider')
            page = inh.input("Give the download page: ", idesc='str')

        ticker = inh.input("Give a downloading ticker to add: ", idesc='str')
        params = (provider, page, ticker)

        q = qb.select('Downloads', keys=dwn_keys)
        res = db.execute(q, params).fetchall()
        if res:
            print('This download is already present', end='\n\n')
        else:
            p = {k: v for k, v in zip(dwn_keys, params)}
            dwn_data.append(columns_data('Downloads', p))

    if dwn_data:
        queries['Downloads'] = (qb.insert('Downloads'), dwn_data)

    # IMPORTS
    import_data = []
    imp_keys = ('uid', 'ticker', 'provider', 'item')
    for d in dwn_data:
        imp_cols = (uid, d[2], d[0])
        msg = "\nAdd a new import for the following download?\n{} {} {} {}\n" \
            .format(*imp_cols, d[1])
        if inh.input(msg, idesc='bool', default=False):
            p = {k: v for k, v in zip(imp_keys, imp_cols)}
            imp_cols = columns_data('Imports', p)

            q = qb.select('Imports', keys=imp_keys)
            res = db.execute(q, imp_cols[:4]).fetchall()
            if res:
                print('This import is already present. Not added', end='\n\n')
            else:
                import_data.append(imp_cols)

    if import_data:
        queries['Imports'] = (qb.insert('Imports'), import_data)

    # Final check
    print('')
    for k, v in queries.items():
        print('Table: {}'.format(k))
        for q in v[1]:
            print('{}'.format(', '.join(map(str, q))), end='\n\n')

    # Final insert
    if inh.input('Do you want to proceed?: ', idesc='bool'):
        for t in queries.values():
            query, data = t
            db.executemany(query, data)
        print('Insert done')

    print("All done!")
