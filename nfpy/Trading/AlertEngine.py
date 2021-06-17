#
# Alert engine class
# Class to create alerts
#

from collections import namedtuple
from itertools import groupby
from typing import Sequence

import numpy as np

from nfpy.Assets import get_af_glob
import nfpy.DB as DB
import nfpy.Financial.Math as Mat
import nfpy.IO as IO
from nfpy.Tools import (Singleton, Utilities as Ut)

from . import Trends as Tr

Alert = namedtuple('Alert', ['uid', 'dt', 'cond', 'value'])


class AlertResult(Ut.AttributizedDict):
    """ Result object from the AlertEngine. """

    def __init__(self):
        super().__init__()
        self.uid = ''
        self.dt = None
        self.p = None
        self.vola = None
        self.w_sr = ()
        self.sr_list = ()
        self.breaches = np.empty(0)
        self.testing = np.empty(0)
        self.alerts = []

    def plot(self) -> IO.TSPlot:
        vola = float(np.nanstd(self.p))
        f_min = np.nanmin(self.p) - 1.65 * vola
        f_max = np.nanmax(self.p) + 1.65 * vola
        dt_min, dt_max = self.dt[-self.w_check], self.dt[-1]

        pl = IO.TSPlot()
        pl.lplot(0, self.dt, self.p)
        pl.line(0, 'v', dt_min, (f_min, f_max), colors='C2', linewidth=1.)
        pl.set_limits(0, 'y', f_min, f_max)

        # FIXME: generalize to n < 'something reasonable' elements
        for sr, color in zip(self.sr_list, ['dimgray', 'sandybrown']):
            idx = np.where((sr > f_min) & (sr < f_max))
            sr = sr[idx[0]]
            pl.line(0, 'h', sr, (self.dt[0], self.dt[-1]),
                    colors=color, linewidth=1.)
            for v in sr:
                corners = (dt_min, v * (1. - self.vola),
                           dt_max, v * (1. + self.vola))
                pl.fill(0, 'r', corners, edgecolor='C2',
                        facecolor='C2', alpha=.2)

        return pl


class AlertEngine(metaclass=Singleton):
    """ Engine to handle and raise alerts. """

    _TABLE = 'Alerts'
    _Q_GET_ALERT = 'select * from Alerts;'
    _Q_ADD_ALERT = 'insert into Alerts (uid, date, cond, value) values (?, ?, ?, ?);'
    _Q_RMV_ALERT = 'delete from Alerts where uid = ? and date = ?;'

    def __init__(self) -> None:
        self._db = DB.get_db_glob()
        self._af = get_af_glob()
        # self._w_slow = 120
        # self._w_fast = 21
        self._sr_mult = 5.
        self._w_check = 10
        self._confidence = 1.65
        self._w_sr = (120, 21)

        self._alerts = {}

        self._initialize()

    def _initialize(self) -> None:
        res = self._db.execute(self._Q_GET_ALERT).fetchall()
        res.sort(key=lambda f: f[0])
        for k, g in groupby(res, key=lambda f: f[0]):
            ll = []
            for v in g:
                uid, date, cond, value = v
                date = np.datetime64(date)
                ll.append(Alert(uid, date, cond, value))
            self._alerts[k] = ll

    def add_alert(self, uid: str, date: np.datetime64,
                  cond: str, value: float) -> None:
        """ Add a manual alert. """
        self._alerts[uid].append(Alert(uid, date, cond, value))
        self._db.execute(self._Q_ADD_ALERT, (uid, date, cond, value))

    def remove_alert(self, uid: str, date: np.datetime64,
                     cond: str, value: float) -> None:
        """ Remove a manual alert. """
        al = self._alerts[uid]
        cmp = Alert(uid, date, cond, value)
        for _ in range(len(al)):
            a = al.pop()
            if a != cmp:
                al.append(a)
        self._db.execute(self._Q_RMV_ALERT, (uid, date, cond, value))

    def list_alerts(self, uid: str) -> list:
        """ List set manual alerts. """
        return self._alerts[uid] if uid in self._alerts else []

    def _raise_alerts(self, uid: str, p: float, out: AlertResult = None) \
            -> Sequence:
        """ Raise manual alerts by verifying the condition. """
        # New object if needed
        if out is None:
            out = AlertResult()

        # Quick exits
        if uid not in self._alerts:
            return out

        al = self._alerts[uid]
        n = len(al)
        if n == 0:
            return out

        # Check alert condition
        breach = []
        for _ in range(n):
            a = al.pop()
            if ((a.cond == 'G') & (p > a.value)) | \
                    ((a.cond == 'L') & (p < a.value)):
                breach.append((a.cond, a.value))
            else:
                al.append(a)

        out.uid = uid
        out.alerts = breach
        return out

    def _calculate_sr(self, dt: np.ndarray, p: np.ndarray) -> Sequence:
        # Support/resistances
        sr_groups = []
        for w in self._w_sr:
            n = int(w * self._sr_mult)
            sr = Tr.search_sr(dt[-n:], p[-n:], w=w, dump=.75)
            sr_groups.append(sr)

        return sr_groups

    def _raise_sr(self, uid: str, dt: np.ndarray, p: np.ndarray,
                  r: np.ndarray, out: AlertResult = None) -> AlertResult:
        # New object if needed
        if out is None:
            out = AlertResult()

        # Get volatility calculated over the cross window
        vola = float(np.nanstd(r))

        # Calculate S/R lines
        sr_groups = Tr.merge_sr(vola, self._calculate_sr(dt, p))
        sr_list = np.sort(np.concatenate(sr_groups))

        # Get the min and max value of the price series over the cross window
        p_c = p[-self._w_check:]
        p_start = Mat.next_valid_value(p_c)[0]
        p_min, p_max = np.nanmin(p_c), np.nanmax(p_c)

        # Run over S/R lines and search for lines in the price range
        vola *= self._confidence
        breach, testing = np.empty(0), np.empty(0)
        idx = np.searchsorted(sr_list, sorted((p_min * (1. - vola),
                                               p_max * (1. + vola))))
        rng = list(range(*idx))
        if len(rng) > 0:
            sr_list = sr_list[rng]
            final = np.where(sr_list <= p_start,
                             sr_list / p_min - 1., p_max / sr_list - 1.)
            breach = sr_list[np.where(final > vola)[0]]
            testing = sr_list[np.where((-vola < final) & (final < vola))[0]]

        w = int(10. * self._w_check)
        out.uid = uid
        out.dt = dt[-w:]
        out.p = p[-w:]
        out.w_sr = self._w_sr
        out.sr_list = sr_groups
        out.breaches = breach
        out.testing = testing
        out.vola = vola
        out.w_check = self._w_check
        return out

    def raise_breaches(self, uid: str, sr: bool = False,
                       alerts: bool = False) -> AlertResult:
        # Quick exit
        out = AlertResult()
        if (not sr) & (not alerts):
            return out

        # Get asset, prices and returns
        asset = self._af.get(uid)
        prices = asset.prices
        dt = prices.index.values
        p = prices.values

        if alerts:
            out = self._raise_alerts(uid, float(p[-1]), out=out)
        if sr:
            r = asset.returns.values[-self._w_check:]
            out = self._raise_sr(uid, dt, p, r, out=out)

        return out


def get_ae_glob() -> AlertEngine:
    """ Returns the pointer to the global AlertEngine """
    return AlertEngine()
