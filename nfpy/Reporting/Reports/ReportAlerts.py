#
# Alerts Report
# Report class for the Market Alerts
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
        'w_alerts_days': 14
    }

    def _init_input(self, type_: Optional[str] = None) -> None:
        """ Prepare and validate the the input parameters for the model. This
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
            triggered=None,
            date_checked=check_start
        )
        alerts.sort(key=lambda k: (k.uid, k.value))

        data = []
        for a in alerts:
            asset = self._af.get(a.uid)
            if asset.type == 'Equity':
                key = asset.ticker
            else:
                key = a.uid
            is_today = 'NEW' if a.date_triggered == dt_today else ''
            dt_trigger = a.date_triggered.strftime('%Y-%m-%d') \
                if a.date_triggered else ''

            data.append((a.uid, key, a.cond, a.value,
                         asset.last_price()[0], is_today, dt_trigger))

        if len(data) > 0:
            df = pd.DataFrame(
                data,
                columns=('ticker', 'uid', 'condition', 'price',
                         'last price', 'new', 'date trigger')
            )
            res.alerts_table = df.style.format(
                formatter={
                    'price': '{:,.2f}'.format,
                    'last price': '{:,.2f}'.format,
                },
                **PD_STYLE_PROP) \
                .set_table_attributes('class="dataframe"') \
                .render()
        else:
            res.alerts_table = f'No breached alerts found'
