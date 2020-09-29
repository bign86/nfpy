import csv
from os.path import join

import numpy as np
import pandas as pd

from nfpy.Handlers.Configuration import get_conf_glob
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.1'
_TITLE_ = "<<< Import into elaboration database script >>>"
# _T = {0: 1, 2: 2, 1: 3}
_COLS = ['ticker', 'date', 'price', 'open', 'high', 'low', 'volume']


def translate(fin: str, ticker: str):
    folder = get_conf_glob().backup_dir
    bond = csv.reader(open(join(folder, fin), 'r'), delimiter='\t')
    data = []

    for line in bond:
        row = [ticker, None, None, None, None, None, None]
        for n, f in enumerate(line, start=1):
            # if n in _T:
            if n == 1:
                v = pd.to_datetime(f.strip()).strftime('%Y-%m-%d')
            else:
                if '%' in f:
                    continue
                v = f.strip().replace(',', '').replace('-', '')
                if not v:
                    v = None
                elif 'M' in v:
                    v = int(float(v.replace('M', '')) * 1e6)
                elif 'B' in v:
                    v = int(float(v.replace('B', '')) * 1e9)
                else:
                    v = float(v)
            # else:
            #    continue
            # row[_T[n]] = v
            row[n] = v
        data.append(row)

    data = np.array(data)
    print(data.shape)

    df = pd.DataFrame(data, columns=_COLS)
    df.info()

    fbak = join(folder, 'investing.csv')
    df.to_csv(fbak, columns=_COLS, header=True, index=False)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    inh = InputHandler()

    fin = inh.input('Insert file name: ', idesc='str')
    ticker = inh.input('Insert ticker: ', idesc='str')
    translate(fin, ticker)

    print("All done!")
