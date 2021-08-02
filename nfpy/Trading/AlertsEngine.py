#
# Alerts engine class
# Class to evaluate manual alerts
#

from collections import namedtuple
# from collections import (defaultdict, namedtuple)
# from itertools import groupby
from typing import Union

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.DB as DB

Alert = namedtuple('Alert',
                   'uid, date, cond, value, triggered, date_triggered, date_checked')


class AlertsEngine(object):
    """ Engine to evaluate and raise manual alerts. """

    _TABLE = 'Alerts'
    _Q_ADD_ALERT = f"insert into Alerts (uid, date, cond, value, triggered," \
                   f"date_triggered) values (?, ?, ?, ?, ?, ?);"
    _Q_RMV_ALERT = f"delete from Alerts where uid = ? and date = ?" \
                   f" and cond = ? and value = ? and triggered = ?;"

    def __init__(self) -> None:
        # Handlers
        self._af = get_af_glob()
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()

    def fetch(self, uid: [str] = (), triggered: Union[None, bool] = False,
              date_triggered: Cal.TyDatetime = None,
              date_checked: Cal.TyDatetime = None) -> [Alert]:
        """ Fetch alerts from the database according to given filters.

            Input:
                uid [[str]]: sequence of uids to load
                triggered [Union[None, bool]]: triggered status of fetched alerts:
                    * True = only triggered alerts
                    * False = only valid alerts
                    * None = any alert
                date_triggered [Cal.TyDatetime]: lower limit for trigger date
                date_checked [Cal.TyDatetime]: upper limit for last check date
        """
        # Apply filters
        keys, data = [], []
        if triggered is not None:
            keys.append('triggered')
            data.append(triggered)

        # Where condition
        where = []
        if len(uid) == 1:
            where.append(f'uid = "{uid[0]}"')
        elif len(uid) > 1:
            uid_list = "\', \'".join(uid)
            where.append(f'uid in (\'{uid_list}\')')

        if date_checked is not None:
            where.append(f'(date_checked <= ? or date_checked is NULL)')
            data.append(date_checked)

        if date_triggered:
            where.append(f'date_triggered >= ?')
            data.append(date_triggered)

        # Fetch data
        res = sorted(
            map(
                Alert._make,
                self._db.execute(
                    self._qb.select(
                        self._TABLE,
                        keys=keys,
                        where=' and '.join(where)
                    ),
                    data
                ).fetchall()
            ),
            key=lambda f: f[0]
        )

        return res

    def _save(self, breached: [Alert], alerts: [Alert]) -> None:
        """ Function to update the Alerts table in the database at object
            destruction time.
        """
        # Update breached alerts
        if len(breached) > 0:
            self._db.executemany(
                self._qb.update(
                    self._TABLE,
                    fields=('triggered', 'date_triggered', 'date_checked')
                ),
                (
                    (*b[4:7], *b[:4])
                    for b in breached
                ),
                commit=True
            )

        # Update the control date on the non-breached alerts
        today = Cal.today(mode='datetime')
        if len(alerts) > 0:
            self._db.executemany(
                self._qb.update(
                    self._TABLE,
                    fields=('date_checked',),
                ),
                (
                    (*al[:4], today)
                    for al in alerts
                ),
                commit=True
            )

    def add(self, alerts: [Alert]) -> None:
        """ Add a manual alert to the database. """
        self._db.executemany(self._Q_ADD_ALERT, alerts, commit=True)

    def remove(self, alerts: [Alert]) -> None:
        """ Remove a manual alert from filtered and database. """
        self._db.executemany(
            self._Q_RMV_ALERT,
            (
                (*a[:5],)
                for a in alerts
            ),
            commit=True)

    def raise_alerts(self, uids: [str] = (),
                     date_checked: Cal.TyDatetime = None) -> [Alert]:
        """ Raise manual alerts for given <uids> by verifying the condition.

            Input:
                uids [[str]]: UIDs to raise alerts for
                date_checked [Cal.TyDatetime]: lower limit for last check date
        """
        # Fetch and quick exit
        alerts = self.fetch(uids, triggered=False, date_checked=date_checked)
        if not alerts:
            return []

        # Quick exit
        breached, idx = [], []
        prices = {}
        today = Cal.today(mode='datetime')
        for i, al in enumerate(alerts):
            # Get last price
            if al.uid not in prices:
                p = self._af \
                    .get(al.uid) \
                    .last_price()[0]
                prices[al.uid] = p
            else:
                p = prices[al.uid]

            if ((al.cond == 'G') & (p > al.value)) | \
                    ((al.cond == 'L') & (p < al.value)):
                idx.append(i)

        breached = [
            Alert(*alerts.pop(i)[:4], True, today, today)
            for i in idx[::-1]
        ]

        # Update the database
        self._save(breached, alerts)
        return breached
