#
# Create New Download script
# Register a new financial item in the database.
#

import nfpy.Assets as As
import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.5'
_TITLE_ = '<<< Create new download script >>>'


def columns_data(_table: str, _data: dict) -> tuple:
    _cols = qb.get_columns(_table)
    _d = []
    for _n, _c in _cols.items():
        if _n in _data:
            _d.append(_data[_n])
            continue
        _col_type = DB.SQLITE2PY_CONVERSION[_c.type]
        _opt = not (_c.is_primary | _c.notnull)
        _check = _n if _n in ('currency', 'isin') else None
        _hint = _c.type + ', OPTIONAL' if _opt else _c.type
        _v = inh.input('Insert {} ({}): '.format(_n, _hint),
                       idesc=_col_type, checker=_check, optional=_opt)
        _d.append(_v)

    return tuple(_d)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = As.get_af_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    dwn = Dwn.get_dwnf_glob()
    inh = IO.InputHandler()

    # Variables
    skip_elaboration = False
    queries, data = {}, {}

    # Choose a UID
    uid = inh.input('Give a UID: ', idesc='str')
    if af.exists(uid):
        skip_elaboration = True
        a_type = af.get_type(uid)
        print(f'UID has been found in the database:\n{a_type} {uid}', end='\n\n')
    else:
        # Asset type
        at, at_idx = af.asset_types, -1
        Ut.print_sequence(at, showindex=True)
        while (at_idx < 0) or (at_idx > len(at)):
            at_idx = inh.input('Insert asset_type index: ', idesc='int')
        a_type = at[at_idx]
        a_obj = Ut.import_symbol('.'.join(['nfpy.Assets', a_type, a_type]))
        table = a_obj._BASE_TABLE
        asset_data = columns_data(table, {'uid': uid})
        queries[table] = (qb.insert(table), (asset_data,))

    # DOWNLOADS
    dwn_data = []
    dwn_keys = ('provider', 'page', 'ticker')
    while inh.input('Add new download?: ', idesc='bool', default=False):
        # Provider
        providers, prov_idx = tuple(dwn.providers), -1
        Ut.print_sequence(providers, showindex=True)
        while (prov_idx < 0) or (prov_idx > len(providers)):
            prov_idx = inh.input('Give the provider index: ', idesc='int')
        provider = providers[prov_idx]

        # Page
        pages, pg_idx = dwn.pages(provider), -1
        Ut.print_sequence(pages, showindex=True)
        while (pg_idx < 0) or (pg_idx > len(pages)):
            pg_idx = inh.input('Give the download page index: ', idesc='int')
        page = pages[pg_idx]

        # Ticker
        ticker = inh.input('Give a downloading ticker to add: ', idesc='str')

        # Compile data
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
        msg = f'\nAdd a new import for the following download?\n{uid} {d[2]} {d[0]} {d[1]}\n'
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
        print(f'\nTable: {k}')
        for q in v[1]:
            print(f"{', '.join(map(str, q))}")

    # Final insert
    if inh.input('\nDo you want to proceed?: ', idesc='bool'):
        for t in queries.values():
            db.executemany(*t)
        print('Insert done')

    print('All done!')
