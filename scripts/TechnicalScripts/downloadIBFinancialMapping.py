#
# Download Single Asset
# Script to download from internet a single page
#

import xml.etree.ElementTree as ET

import nfpy.DB as DB
from nfpy.Downloader.IBApp import IBAppFundamentals
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

__version__ = '0.3'
_TITLE_ = "<<< Interactive Brokers financials mapping download script >>>"


def ibdownload(tck_, ccy_, cf_, req_) -> str:
    app = IBAppFundamentals(req_)
    app.addContracts(tck_, ccy_)
    app.connect(cf_.ib_interface, cf_.ib_tws_port, cf_.ib_client_id)
    app.run()
    return app.return_data


def parsexml(data_) -> tuple:
    ib_tree = ET.fromstring(data_)
    ib_stats = ib_tree.find('FinancialStatements')
    ib_map = ib_stats.find('COAMap')

    data_map, data_dt = list(), list()
    for item in ib_map.findall('mapItem'):
        coa = item.get('coaItem')
        stat = item.get('statementType')
        lid = int(item.get('lineID')) + 10000
        name = item.text
        data_map.append((coa, stat, name))
        data_dt.append((coa, lid))

    return set(data_map), set(data_dt)


def fetchfromdb(db_, qb_) -> tuple:
    avail_map = db_.execute(qb_.selectall('MapFinancials')).fetchall()
    sel_dt = qb_.select('DecDatatype', keys=(), rolling=['encoding'])
    avail_dt = db_.execute(sel_dt, (10001, 19999)).fetchall()
    return set(avail_map), set(avail_dt)


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    conf = get_conf_glob()

    ticker = ['PST', 'BVME']
    provider = 'IB'
    page = 'Financials'
    ccy = 'EUR'
    req = 'ReportsFinStatements'
    save = False

    new_map, new_dt = parsexml(
        ibdownload(ticker, ccy, conf, req)
    )
    old_map, old_dt = fetchfromdb(db, qb)

    diff_map = new_map - old_map
    diff_dt = new_dt - old_dt
    print(
        f'Downloaded\tmaps: {len(new_map)}\t-\tdatatypes: {len(new_dt)}\n'
        f'Existing\tmaps: {len(old_map)}\t-\tdatatypes: {len(old_dt)}\n'
        f'To be added\tmaps: {len(diff_map)}'
    )

    if save:
        map_q = qb.insert('MapFinancials')
        db.executemany(map_q, diff_map)
    else:
        _nl = '\n'.join(list(diff_map))
        print(f'MapFinancials\n{_nl}')

    Ut.print_ok('All done!')
