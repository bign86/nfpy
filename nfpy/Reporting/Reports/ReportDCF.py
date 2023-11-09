#
# Report Market Short
# Report class for the short report on market data
#

from collections import defaultdict
import numpy as np
import pandas as pd
from typing import (Any, Optional)

from nfpy.Assets import TyAsset
from nfpy.Financial.EquityValuation import DCF
import nfpy.IO as IO
from nfpy.Tools import (
    Exceptions as Ex,
    Utilities as Ut
)

from .BaseReport import BaseReport

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportDCF(BaseReport):

    def _one_off_calculations(self) -> None:
        """ Perform all non-uid dependent calculations for efficiency. """
        pass

    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """
        outputs = defaultdict(dict)
        uid = self.uids[0]
        print(f'  > {uid}')
        try:
            asset = self._af.get(uid)
            if asset.type != 'Equity':
                raise Ex.AssetTypeError(f'ReportDCF(): {uid} is not an equity')

            res = Ut.AttributizedDict()
            self._calc_dcf(asset, res)
            outputs[asset.ticker] = res

        except (RuntimeError, ValueError, Ex.AssetTypeError) as ex:
            Ut.print_exc(ex)

        return outputs

    def _calc_dcf(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'description', 'ticker', 'isin', 'country',
                      'currency', 'company', 'index')
        }

        # Relative path in results object
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('DCF',),
                ('p_price', 'fundamentals', 'rates')
            )
        )
        res.img_p_price = fig_rel[0]
        res.img_fundamentals = fig_rel[1]
        res.img_rates = fig_rel[2]

        # Discounted Cash Flow Calculation
        try:
            dcf_res = DCF(asset.uid, **self._p) \
                .result(**self._p)
        except (Ex.MissingData, ValueError) as ex:
            res.has_dcf = False
            Ut.print_exc(ex)
            return

        #  if not dcf_res.success:
        #     res.has_dcf = False
        #     res.last_price = dcf_res.last_price
        #     return
        #
        # else:
        res.has_dcf = True
        res.dcf_success = dcf_res.success
        res.dcf_msg = dcf_res.msg

        if dcf_res.applicable:
            res.dcf_fair_value = dcf_res.outputs['fair_value']
            res.dcf_return = dcf_res.outputs['ret'] * 100.
            res.dcf_wacc = dcf_res.outputs['wacc'] * 100.
            res.dcf_coe = dcf_res.outputs['cost_of_equity'] * 100.
            res.dcf_cod = dcf_res.outputs['cost_of_debt'] * 100.
            res.dcf_lt_gwt = dcf_res.outputs['lt_growth'] * 100.
            res.dcf_tot_gwt = dcf_res.outputs['tot_growth'] * 100.

            res.dcf_inputs = self._p

            # Calculations table
            fcff_calcs = dcf_res.outputs['fcff_calc']
            res.fcff_calcs = fcff_calcs \
                .to_html(
                    index=True,
                    na_rep='-',
                    border=None,
                    formatters={
                        'fcf': '{:,.2E}'.format,
                        'calc_fcf': '{:,.2E}'.format,
                        'revenues': '{:,.2E}'.format,
                        '\u0394% revenues': '{:,.1%}'.format,
                        'cfo': '{:,.2E}'.format,
                        'cfo cov.': '{:,.1%}'.format,
                        'capex': '{:,.2E}'.format,
                        'capex cov.': '{:,.1%}'.format,
                    },
                )

            # Last price
            last_price, last_price_dt, _ = asset.last_price()
            res.last_price = last_price
            res.last_price_date = str(last_price_dt)[:10]

            # Prices: full history plot
            prices = asset.prices
            ath_idx = np.argmax(prices)
            atl_idx = np.argmin(prices)
            ath_ret = prices[ath_idx] / last_price - 1.
            atl_ret = prices[atl_idx] / last_price - 1.

            # Plotting
            _ = IO.TSPlot(x_zero=[.0]) \
                .lplot(0, prices, color='k', linewidth=.75) \
                .annotate(0, f' {last_price:.2f}', (last_price_dt, last_price), fontsize=12) \
                .annotate(0, f'{ath_ret:.1%}', (prices.index[ath_idx], prices[ath_idx]),
                          fontsize=12, color='forestgreen', ha='right', va='bottom') \
                .annotate(0, f'{atl_ret:.1%}', (prices.index[atl_idx], prices[atl_idx]),
                          fontsize=12, color='firebrick', ha='right', va='top') \
                .line(0, 'xh', dcf_res.outputs['fair_value'], color='C0', label='fair value') \
                .plot() \
                .save(fig_full[0]) \
                .clf()

            _ = IO.TSPlot(yl=('Value',)) \
                .lplot(0, fcff_calcs.revenues, label='revenues') \
                .lplot(0, fcff_calcs.calc_fcf, label='FCFF') \
                .lplot(0, fcff_calcs.cfo, label='CFO') \
                .lplot(0, fcff_calcs.capex, label='CAPEX') \
                .plot() \
                .save(fig_full[1]) \
                .clf()

            _ = IO.TSPlot(yl=('% Rate',), x_zero=[.0]) \
                .lplot(0, fcff_calcs['\u0394% revenues'], label='revenues growth') \
                .lplot(0, fcff_calcs['cfo cov.'], label='CFO cov.') \
                .lplot(0, fcff_calcs['capex cov.'], label='CAPEX cov.') \
                .plot() \
                .save(fig_full[2]) \
                .clf()
