#
# Financials Synthetic provider
# Used to coalesce the financials data from different providers
#

import pandas.tseries.offsets as off

from nfpy.Tools import Utilities as Ut

from .BaseProvider import BaseImportItem
from .DownloadsConf import (
    IBFinancialsMapping,  # InvestingFinancialsMapping,
    YahooFinancialsMapping
)


class FinancialsItem(BaseImportItem):
    _PROVIDERS = [
        ('IB', 'IBFinancials', IBFinancialsMapping),
        ('Yahoo', 'YahooFinancials', YahooFinancialsMapping),
        # ('Investing', 'InvestingFinancials', InvestingFinancialsMapping),
    ]
    _MODE = 'SPLIT'
    _Q_READ = """select distinct '{uid}', statement, code, date, freq, value
    from {src_table} where ticker = ?"""
    _Q_WRITE = """insert or replace into {dst_table}
    (uid, code, date, freq, value) values (?, ?, ?, ?, ?)"""

    @staticmethod
    def _create_list(data: dict) -> list[tuple]:
        """ Prepare results for import. """
        return [
            (v[0], *k, v[1])
            for k, v in data.items()
        ]

    def _provider_data(self) -> tuple:
        tck_list = self._d['ticker'].split('/')
        for tck, prov in zip(tck_list, self._PROVIDERS):
            yield tck, *prov

    def run(self) -> None:
        data_dict = {}
        uid = self._d['uid']

        for prov_data in self._provider_data():

            new_data = {}

            # If the ticker is not present, the provider is not available
            if prov_data[0] == '':
                continue

            # Fetch provider data
            qr = self._Q_READ.format(src_table=prov_data[2], uid=uid) + ';'
            data = self._db.execute(qr, (prov_data[0],)).fetchall()

            # If no data exists exit
            if len(data) == 0:
                continue

            mapping = prov_data[3]
            while data:
                item = data.pop(0)

                # Map the field
                try:
                    field = mapping[item[1]][item[2]]
                except KeyError as ex:
                    Ut.print_exc(ex)
                    continue

                if field[0] == '':
                    continue

                # Adjust the date
                dt = item[3] - off.BDay(10)
                ref = off.BMonthEnd() \
                    .rollforward(dt) \
                    .strftime('%Y-%m-%d')

                key = (field[0], ref, item[4])

                # Check if the data is already present and in case skip it
                if key in data_dict:
                    continue

                # Check if the data was already present in the new data
                if key in new_data:
                    # If there is a new data already present with higher
                    # priority (lower number) then we skip it
                    if field[1] > new_data[key][2]:
                        continue

                # Adjust the base
                value = item[5] * field[2]

                # If we are here it means that the new data point is not in the
                # data from other providers, not in the new data, or in the new
                # data but with lower priority. Hence, we add it to the new data
                new_data[key] = (uid, value, field[1])

            # We add all new data to the general results dictionary
            data_dict.update(new_data)

        # When all providers are done, we transform the dictionary into a tuple
        # for insertion in the database
        data_clean = self._create_list(data_dict)

        if len(data_clean) > 0:
            self._db.executemany(
                self._Q_WRITE.format(**self._d),
                data_clean,
                commit=True
            )
