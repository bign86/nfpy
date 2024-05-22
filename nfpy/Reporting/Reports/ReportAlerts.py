#
# Alerts Report
# Class for the Market Alerts
#

from datetime import timedelta
import pandas as pd
from typing import (Any, Optional)

import nfpy.IO.Utilities
from nfpy.Calendar import today
from nfpy.Tools import (
    Exceptions as Ex,
    Utilities as Ut
)
import nfpy.Trading as Trd

from .BaseReport import (BaseReport, ReportData)

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportAlerts(BaseReport):

    def __init__(self, data: ReportData, path: Optional[str] = None):
        super().__init__(data, path)

        self._sr_tol = float(self._p['tolerance'])
        self._w_sr = self._p['w_sr']
        self._sr_check = int(self._p['w_check'])
        self._smooth_w = max(self._w_sr) + self._sr_check + 1

        if len(self._cal.calendar) < self._sr_check:
            raise Ex.CalendarError(f'ReportAlerts(): calendar too short to have {self._smooth_w} periods')

    def _one_off_calculations(self) -> None:
        """ Perform all non-uid dependent calculations for efficiency. """
        pass

    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """
        self._one_off_calculations()
        outputs = Ut.AttributizedDict()

        try:
            self._check_alerts(outputs)
        except (RuntimeError, Ex.AssetTypeError) as ex:
            nfpy.IO.Utilities.print_exc(ex)

        return outputs

    def _check_alerts(self, res: Ut.AttributizedDict) -> None:
        # Manual alerts
        ae = Trd.AlertsEngine()
        _ = ae.trigger()
        ae.update_db()

        dt_today = today(mode='datetime')
        check_start = dt_today - timedelta(days=self._p['w_start_check'])
        alerts = ae.fetch(
            triggered=True,
            date_checked=check_start
        )

        # if alerts:
        #     keys = set(k.uid for k in alerts)
        # alerts.sort(key=lambda k: (k.uid, k.value))

        data = []
        data_dict = {}
        for a in alerts:
            asset = self._af.get(a.uid)
            key = asset.ticker if asset.type == 'Equity' else a.uid
            is_today = 'NEW' if a.date_triggered == dt_today else ''
            dt_trigger = a.date_triggered.strftime('%Y-%m-%d')

            data.append((key, a.uid, a.cond, a.value, asset.last_price()[0],
                         'breach', is_today, dt_trigger))

            d = data_dict.get(key, {'manual': []})
            d['manual'].append(
                (
                    a.uid, a.cond, a.value, asset.last_price()[0],
                    'breach', is_today, dt_trigger
                 )
            )
            data_dict[key] = d

        # S/R alerts
        for uid in self._uids:
            eq = self._af.get(uid)
            v_p = eq.prices.values[-self._smooth_w:]
            key = eq.ticker if eq.type == 'Equity' else uid
            last_price = eq.last_price()[0]

            sr_checker = Trd.SRBreachEngine(
                v_p, self._sr_check, self._sr_tol,
                'smooth', self._w_sr
            )
            sr = sr_checker.get(triggers_only=True)

            if sr:
                d = data_dict.get(key, {'SR': []})
                if 'SR' not in d:
                    d['SR'] = []

                for b in sr:
                    data.append((key, uid, b[0], b[1], last_price, b[2], '', ''))

                    d['SR'].append(
                        (uid, b[0], b[1], last_price, b[2], '', '')
                    )

                data_dict[key] = d

        # Create final table of alerts
        if len(data) > 0:
            data.sort(key=lambda k: (k[0], k[3]))

            df = pd.DataFrame(
                data,
                columns=['ticker', 'uid', 'condition', 'price',
                         'last price', 'status', 'new', 'date trigger']
            )
            res.alerts_table = df.to_html(
                formatters={
                    'price': '{:,.2f}'.format,
                    'last price': '{:,.2f}'.format,
                },
                **PD_STYLE_PROP
            )
        else:
            res.alerts_table = f'No breached alerts found'

        res.alerts_data = data_dict
