#
# Create New Download script
# Register a new financial item in the database.
#

import nfpy.Assets as As
import nfpy.DB as DB
import nfpy.Downloader as Dwn
import nfpy.IO as IO
import nfpy.IO.Utilities as IOUt
from nfpy.Tools import Utilities as Uti

__version__ = '0.7'
_TITLE_ = '<<< Create new download script >>>'
__desc__ = """
The script creates a new download by adding relevant entries into both the
Download and the Import tables, as well as in the elaboration tables if the
asset is not already known in the database.
"""

_IMPORT_HINTS = {
    'HistoricalPrices': 'ClosePrices',
    'Splits': 'Splits',
    'Dividends': 'Dividends',
    'Financials': 'Financials',
    'Series': 'ClosePrices',
}


def columns_data(_table: str, _data: dict, *args) -> tuple:
    _cols = qb.get_columns(_table)
    _d = []
    for _n, _c in _cols.items():
        if _n in _data:
            _d.append(_data[_n])
            continue

        if _n in ('country', 'currency', 'isin'):
            _col_type = _n
        else:
            _col_type = DB.SQLITE2PY_CONVERSION[_c.type]
        _opt = not (_c.is_primary | _c.notnull)
        _hint = _c.type + ', OPTIONAL' if _opt else _c.type

        if _n == 'item':
            _default = _IMPORT_HINTS[args[0]]
            _msg = f'Insert {_n} ({_default}): '
        else:
            _msg = f'Insert {_n} ({_hint}): '
            _default = None

        _v = inh.input(_msg, idesc=_col_type, optional=_opt, default=_default)
        _d.append(_v)

    return tuple(_d)


if __name__ == '__main__':
    IOUt.print_header(_TITLE_, end='\n\n')

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
        a_type = af.get_asset_type(uid)
        print(f'UID has been found in the database:\n{a_type} {uid}', end='\n\n')
    else:
        # Asset type
        types = sorted(af.asset_types)
        IOUt.print_sequence(types, showindex=True)
        at_idx = inh.input(
            'Insert asset_type index: ',
            idesc='index', limits=(0, len(types)-1)
        )
        a_type = types[at_idx]
        a_obj = Uti.import_symbol('.'.join(['nfpy.Assets', a_type, a_type]))
        table = a_obj._BASE_TABLE
        queries[table] = (
            qb.insert(table),
            (columns_data(table, {'uid': uid}),)
        )

    # DOWNLOADS
    dwn_data = []
    dwn_keys = ('provider', 'page', 'ticker')
    while inh.input('Add new download (default False)?: ', idesc='bool', default=False):
        # Provider
        providers = tuple(dwn.providers)
        IOUt.print_sequence(providers, showindex=True)
        prov_idx = inh.input(
            'Give the provider index: ',
            idesc='index', limits=(0, len(providers)-1)
        )
        provider = providers[prov_idx]

        # Page
        pages = dwn.pages(provider)
        IOUt.print_sequence(pages, showindex=True)
        pg_idx = inh.input(
            'Give the download page index: ',
            idesc='index', limits=(0, len(pages)-1)
        )
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
    q_sel_imp = qb.select('Imports', keys=imp_keys)
    for d in dwn_data:
        imp_cols = (uid, d[2], d[0])
        msg = f'\nAdd a new import for the following download?\n{uid} {d[2]} {d[0]} {d[1]}\n'
        if inh.input(msg, idesc='bool', default=False):
            p = {k: v for k, v in zip(imp_keys, imp_cols)}
            imp_cols = columns_data('Imports', p, d[1])

            res = db.execute(q_sel_imp, imp_cols[:4]).fetchall()
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
    if inh.input('\nDo you want to proceed?: ', idesc='bool', default=False):
        for t in queries.values():
            db.executemany(*t)
        print('Insert done')

    IOUt.print_ok('All done!')
