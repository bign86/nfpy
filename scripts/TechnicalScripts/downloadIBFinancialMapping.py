#
# Download Single Asset
# Script to download from internet a single page
#

import xml.etree.ElementTree as ET

from nfpy.Downloader.IBApp import IBAppFundamentals
import nfpy.IO as IO
from nfpy.Tools import get_conf_glob

__version__ = '0.2'
_TITLE_ = "<<< Interactive Brokers financials mapping download script >>>"


def ibdownload(tck_, ccy_, cf_) -> str:
    app = IBAppFundamentals()
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
    qb = IO.get_qb_glob()
    db = IO.get_db_glob()
    conf = get_conf_glob()

    ticker = ['KO', '']
    provider = 'IB'
    page = 'Financials'
    ccy = 'USD'
    save = False

    new_map, new_dt = parsexml(ibdownload(ticker, ccy, conf))
    old_map, old_dt = fetchfromdb(db, qb)

    diff_map = new_map - old_map
    diff_dt = new_dt - old_dt
    print('Downloaded\tmaps: {}\t-\tdatatypes: {}'.format(len(new_map), len(new_dt)))
    print('Existing\tmaps: {}\t-\tdatatypes: {}'.format(len(old_map), len(old_dt)))
    print('To be added\tmaps: {}\t-\tdatatypes: {}'.format(len(diff_map), len(diff_dt)))

    if save:
        map_q = qb.insert('MapFinancials')
        dt_q = qb.insert('DecDatatype')
        db.executemany(map_q, diff_map)
        db.executemany(dt_q, diff_dt)
    else:
        print('MapFinancials')
        for v in diff_map:
            print(v)
        print('DecDatatype')
        for v in diff_dt:
            print(v)

    print('done!')
