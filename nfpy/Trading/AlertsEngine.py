#
# Alerts engine class
# Class to evaluate manual alerts
#

from collections import namedtuple
from typing import (Optional, Sequence)

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.DB as DB

Alert = namedtuple(
    'Alert',
    'uid, date, cond, value, triggered, date_triggered, date_checked'
)


class AlertsEngine(object):
    """ Engine to evaluate and raise manual alerts. """

    _TABLE = 'Alerts'
    _Q_ADD_ALERT = f"insert into Alerts (uid, date, cond, value, triggered, " \
                   f"date_triggered, date_checked) values (?, ?, ?, ?, ?, ?, ?);"
    _Q_RMV_ALERT = f"delete from Alerts where uid = ? and date = ?" \
                   f" and cond = ? and value = ? and triggered = ?;"

    def __init__(self) -> None:
        # Handlers
        self._af = get_af_glob()
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()

        self._breached = []
        self._checked = []

    def add(self, alerts: Sequence[Alert]) -> None:
        """ Add a manual alert to the database. """
        self._db.executemany(self._Q_ADD_ALERT, alerts, commit=True)

    def fetch(self, uid: Sequence[str] = (),
              triggered: Optional[bool] = False,
              date_triggered: Optional[Cal.TyDatetime] = None,
              date_checked: Optional[Cal.TyDatetime] = None) -> list[Alert]:
        """ Fetch alerts from the database according to given filters.

            Input:
                uid [Sequence[str]]: sequence of uids to load
                triggered [Optional[bool]]: triggered status of fetched alerts:
                    * True = only triggered alerts
                    * False = only valid alerts
                    * None = any alert
                date_triggered [Optional[Cal.TyDatetime]]: lower limit for
                    trigger date
                date_checked [Optional[Cal.TyDatetime]]: upper limit for last
                    check date
        """
        # Apply filters
        keys, data = [], []
        if triggered is not None:
            keys.append('triggered')
            data.append(triggered)

        # Where condition
        where = []
        if len(uid) == 1:
            where.append(f'[uid] = "{uid[0]}"')
        elif len(uid) > 1:
            uid_list = "\', \'".join(uid)
            where.append(f'[uid] in (\'{uid_list}\')')

        if date_checked is not None:
            where.append(f'([date_checked] >= ? or [date_checked] is NULL)')
            data.append(date_checked)

        if date_triggered:
            where.append(f'[date_triggered] >= ?')
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

    def remove(self, alerts: Sequence[Alert]) -> None:
        """ Remove a manual alert from filtered and database. """
        self._db.executemany(
            self._Q_RMV_ALERT,
            (
                (*a[:5],)
                for a in alerts
            ),
            commit=True
        )

    def trigger(self, uids: Sequence[str] = (),
                date_checked: Optional[Cal.TyDatetime] = None) -> list[Alert]:
        """ Trigger manual alerts for given <uids> by verifying the condition.

            Input:
                uids [Sequence[str]]: UIDs to raise alerts for
                date_checked [Optional[Cal.TyDatetime]]: lower limit for last
                    check date

            Output:
                breached [list[Alerts]]: list of breached alerts
        """
        alerts = self.fetch(uids, triggered=False, date_checked=date_checked)
        if not alerts:
            return []

        prices, idx = {}, []
        for i, al in enumerate(alerts):
            # Get last price
            if al.uid in prices:
                p = prices[al.uid]
            else:
                p = self._af \
                    .get(al.uid) \
                    .last_price()[0]
                # Add back to the dict as the same uid may appear again
                prices[al.uid] = p

            if ((al.cond == 'G') & (p > al.value)) | \
                    ((al.cond == 'L') & (p < al.value)):
                idx.append(i)

        today = Cal.today(mode='datetime')
        breached = [
            Alert(*alerts.pop(i)[:4], True, today, today)
            for i in idx[::-1]
        ]

        self._breached.extend(list(set(self._breached) | set(breached)))
        self._checked.extend(list(set(self._checked) | set(alerts)))
        return breached

    def update_db(self) -> None:
        """ Function to update the Alerts table in the database at object
            destruction time.
        """
        # Update breached alerts
        if len(self._breached) > 0:
            self._db.executemany(
                self._qb.update(
                    self._TABLE,
                    fields=('triggered', 'date_triggered', 'date_checked')
                ),
                (
                    (*b[4:7], *b[:4])
                    for b in self._breached
                ),
                commit=True
            )
            self._breached = []

        # Update the control date on the non-breached alerts
        today = Cal.today(mode='datetime')
        if len(self._checked) > 0:
            self._db.executemany(
                self._qb.update(
                    self._TABLE,
                    fields=('date_checked',),
                ),
                (
                    (today, *al[:4])
                    for al in self._checked
                ),
                commit=True
            )
            self._checked = []
