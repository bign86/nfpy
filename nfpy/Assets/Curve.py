#
# Curve class
# Aggregation of single rates of different tenors
#

from operator import itemgetter
from typing import Union

import pandas as pd
import numpy as np

from .AggregationMixin import AggregationMixin
from .Asset import Asset
from .AssetFactory import get_af_glob
from nfpy.Tools.Exceptions import MissingData


class Curve(AggregationMixin, Asset):
    """ Class for curves seen as aggregations of buckets. """

    _TYPE = 'Curve'
    _BASE_TABLE = 'Rate'
    _CONSTITUENTS_TABLE = 'CurveConstituents'

    def __init__(self, uid: str):
        super().__init__(uid)
        self._cnsts_tenors = ()

    def _load_cnsts(self):
        """ Fetch from the database the curve constituents. """
        q = self._qb.select(self._CONSTITUENTS_TABLE, fields=["bucket"], keys=["uid"])
        res = self._db.execute(q, (self._uid,)).fetchall()
        if not res:
            raise MissingData('No constituents found for Curve {}'.format(self.uid))

        af = get_af_glob()
        bucket_list = []
        for r in res:
            uid = r[0]
            bucket = af.get(uid)
            bucket.load()
            bucket_list.append((uid, bucket.tenor))
            self._dict_cnsts[uid] = bucket

        bucket_list = sorted(bucket_list, key=itemgetter(1))
        self._cnsts_uids = [b[0] for b in bucket_list]
        self._cnsts_tenors = [b[1] for b in bucket_list]

        for b, t in bucket_list:
            self._cnsts_df[t] = self._dict_cnsts[b].prices

    # TODO: check if it works with a series of dates instead of a single one
    def term_struct(self, date: pd.Timestamp) -> pd.DataFrame:
        """ Gives the cross section of the curve at a given date. """
        return self._cnsts_df.loc[date]

    def bucket_ts(self, uid: str) -> pd.Series:
        """ Gives the bucket time series. """
        return self._cnsts_df[uid]

    # TODO: to be written in some way
    def rate(self, t: float, date: pd.Timestamp) -> Union[float, np.ndarray]:
        """ Return the rate for the given maturity. """
        ts = self.term_struct(date)
        return np.interp(t, ts.index.values, ts.values)
