#
# Alerts Report
# Class for the Market Alerts
#

from datetime import timedelta
import pandas as pd
from typing import (Any, Optional)

from nfpy.Calendar import today
from nfpy.Tools import (
    Exceptions as Ex,
    Utilities as Ut
)
import nfpy.Trading as Trd

from .BaseReport import BaseReport

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportAlerts(BaseReport):
    DEFAULT_P = {
        'years_price_hist': 2.,
        'w_alerts_days': 14,
        'sr': {
            'w_sr': [120, 20],
            'w_check': 10,
            'tolerance': 1.5,
            'w_multi': 2.,
        }
    }

    def _init_input(self, type_: Optional[str] = None) -> None:
        """ Prepare and validate the input parameters for the model. This
            includes verifying the parameters are correct for the models in the
            report. Takes the default parameters if any, applies the values from
            the database and the asset-specific overlays if any.
            The function must ensure the parameters from the database stored in
            the self._p symbol are NOT altered for later usage by making copies
            if required.
        """
        pass

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
            Ut.print_exc(ex)

        return outputs

    def _check_alerts(self, res: Ut.AttributizedDict) -> None:
        # Manual alerts
        ae = Trd.AlertsEngine()
        _ = ae.trigger()
        ae.update_db()

        dt_today = today(mode='datetime')
        check_start = dt_today - timedelta(days=self._p['w_alerts_days'])
        alerts = ae.fetch(
            triggered=True,
            date_checked=check_start
        )
        alerts.sort(key=lambda k: (k.uid, k.value))

        data = []
        for a in alerts:
            asset = self._af.get(a.uid)
            key = asset.ticker if asset.type == 'Equity' else a.uid
            is_today = 'NEW' if a.date_triggered == dt_today else ''
            dt_trigger = a.date_triggered.strftime('%Y-%m-%d')

            data.append((key, a.uid, a.cond, a.value, asset.last_price()[0],
                         'breach', is_today, dt_trigger))

        # S/R alerts
        sr = self._p['sr']
        w_sr = sr['w_sr']
        sr_check = sr['w_check']
        sr_tol = sr['tolerance']
        sr_multi = sr['w_multi']
        smooth_w = max(w_sr) * sr_multi

        for uid in self._uids:
            eq = self._af.get(uid)
            v_p = eq.prices.values[-smooth_w:]
            key = eq.ticker if eq.type == 'Equity' else uid
            last_price = eq.last_price()[0]

            sr_checker = Trd.SRBreach(v_p, sr_check, sr_tol, 'smooth', w_sr)
            for b in sr_checker.get(triggers_only=True):
                data.append((key, uid, b[0], b[1], last_price, b[2], '', ''))

        # Create final table of alerts
        if len(data) > 0:
            data.sort(key=lambda k: (k[0], k[3]))

            df = pd.DataFrame(
                data,
                columns=('ticker', 'uid', 'condition', 'price',
                         'last price', 'status', 'new', 'date trigger')
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
