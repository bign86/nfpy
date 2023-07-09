#
# OECD Downloader
# Downloads data from the OECD central database
#

import json
import pandas as pd
import pandas.tseries.offsets as off

from nfpy.Calendar import today

from .BaseDownloader import (BasePage, DwnParameter)
from .BaseProvider import BaseImportItem
from .DownloadsConf import OECDSeriesConf


class ClosePricesItem(BaseImportItem):
    _MODE = 'SPLIT'
    _Q_READ = """select '{uid}', 114, date_code, value from OECDSeries where ticker = ?"""
    _Q_WRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    values (?, ?, ?, ?)"""
    _Q_INCR = """ and date_code > iif(substr(ticker, length(ticker)) == 'M',
    substr(ifnull((select max(date) from RateTS where uid = '{uid}'),
    '1900-01-01'),1,7),substr(ifnull((select max(date) from RateTS
    where uid = '{uid}'),'1900-01-01'),1,4))"""

    @staticmethod
    def _clean_data(data: list[tuple]) -> list[tuple]:
        """ Prepare results for import. """
        data_ins = []
        while data:
            item = data.pop(0)

            # Adjust the date
            dt = str(item[2])
            if len(dt) == 4:
                dt += '-01-01'
            elif len(dt) == 7:
                dt += '-01'

            # Build the new tuple
            data_ins.append((item[0], item[1], dt, item[3]))

        return data_ins


class SeriesPage(BasePage):
    """ Base class for all OECD downloads. It cannot be used by itself but the
        derived classes for single download instances should always be used.
    """

    _ENCODING = "utf-8-sig"
    _PROVIDER = "OECD"
    _REQ_METHOD = 'get'
    _PAGE = 'Series'
    _COLUMNS = OECDSeriesConf
    _BASE_URL = u"https://stats.oecd.org/SDMX-JSON/data/{dataset_id}/{data_subject}/all?"
    _TABLE = "OECDSeries"
    _Q_MAX_DATE = "select max(date) from OECDSeries where ticker = ?"
    _PARAMS = {
        'startTime': DwnParameter('startTime', True, None),
        'endTime': DwnParameter('endTime', True, None),
        'dimensionAtObservation': DwnParameter('dimensionAtObservation', False, 'allDimensions'),
    }

    def _set_default_params(self) -> None:
        """ Set the starting default of the parameters for the page. """
        defaults = {}
        for p in self._PARAMS.values():
            if p.default is not None:
                defaults[p.code] = p.default

        ld = self._fetch_last_data_point((self._ticker,))
        defaults.update(
            {
                'startTime': pd.to_datetime(ld).strftime('%Y-%m'),
                'endTime': today(mode='str', fmt='%Y-%m')
            }
        )
        self._p = [defaults]

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        request = self._ticker.split('/')

        dataset_id = request[0]
        data_subject = '.'.join(
            [
                '+'.join(p.split(','))
                for p in request[1:]
                if p
            ]
        )

        return self._BASE_URL.format(
            dataset_id=dataset_id, data_subject=data_subject
        )

    def _local_initializations(self, ext_p: dict) -> None:
        """ Page-dependent initializations of parameters. """
        if ext_p:
            translate = {'start': 'startTime', 'end': 'endTime'}
            p = {}
            for ext_k, ext_v in ext_p.items():
                if ext_k in translate:
                    p[translate[ext_k]] = pd.to_datetime(ext_v).strftime('%Y-%m')
            self._p[0].update(p)

    def _parse(self) -> None:
        """ Parse the fetched object. """
        j = json.loads(self._robj[0].text)

        dimensions = j["structure"]["dimensions"]["observation"]
        attributes = j["structure"]["attributes"]["observation"]
        data_points = j["dataSets"][0]["observations"]

        if len(data_points) == 0:
            raise RuntimeWarning(f'{self._ticker} | no new data downloaded')

        location_list = [v for v in dimensions if v['id'] == 'LOCATION'][0]['values']
        measure_list = [v for v in dimensions if v['id'] == 'MEASURE'][0]['values']
        time_list = [v for v in dimensions if v['id'] == 'TIME_PERIOD'][0]['values']
        units_list = [v for v in attributes if v['id'] == 'UNIT'][0]['values']
        powercode_list = [v for v in attributes if v['id'] == 'POWERCODE'][0]['values']

        # Sometimes we have SUBJECT, sometimes TRANSACT
        subject = [v for v in dimensions if v['id'] == 'SUBJECT']
        if not subject:
            subject = [v for v in dimensions if v['id'] == 'TRANSACT']
        subject_list = subject[0]['values']

        frequency = [v for v in dimensions if v['id'] == 'FREQUENCY']
        if not frequency:
            frequency = [{'values': [{'id': 'A', 'name': 'Annually'}]}]
        frequency_list = frequency[0]['values']

        data = []
        for idx, point in data_points.items():
            dims = list(map(int, idx.split(':')))
            row = [
                location_list[dims[0]]['id'],
                location_list[dims[0]]['name'],
                subject_list[dims[1]]['id'],
                subject_list[dims[1]]['name'],
                measure_list[dims[2]]['id'],
                measure_list[dims[2]]['name'],
            ]
            if len(dims) == 4:
                row.extend(
                    [
                        frequency_list[0]['id'],
                        frequency_list[0]['name'],
                        time_list[dims[3]]['id'],
                        time_list[dims[3]]['name'],
                    ]
                )
            elif len(dims) == 5:
                row.extend(
                    [
                        frequency_list[dims[3]]['id'],
                        frequency_list[dims[3]]['name'],
                        time_list[dims[4]]['id'],
                        time_list[dims[4]]['name'],
                    ]
                )
            row.extend(
                [
                    units_list[dims[2]]['id'],
                    units_list[dims[2]]['name'],
                ]
            )
            if len(powercode_list) == 1:
                row.extend(
                    [
                        int(powercode_list[0]['id']),
                        powercode_list[0]['name'],
                        float(point[0])
                    ]
                )
            else:
                row.extend(
                    [
                        int(powercode_list[dims[2]]['id']),
                        powercode_list[dims[2]]['name'],
                        float(point[0])
                    ]
                )
            data.append(row)

        df = pd.DataFrame(data, columns=self._COLUMNS)
        df.insert(0, 'ticker', self._ticker)
        self._res = df
