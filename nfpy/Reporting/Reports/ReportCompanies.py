#
# Companies Report
# Report class for the Companies Data
#

from collections import defaultdict
import numpy as np
import pandas as pd
from typing import (Any, Optional)

from nfpy.Assets import TyAsset
import nfpy.IO as IO
from nfpy.Financial.EquityValuation import (
    DiscountedCashFlowModel, DividendDiscountModel
)
import nfpy.Math as Math
from nfpy.Tools import (
    Constants as Cn,
    Exceptions as Ex,
    Utilities as Ut
)

from .BaseReport import (BaseReport, ReportData)

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportCompanies(BaseReport):
    DEFAULT_P = {
        "d_rate": 0.00,
        "baseData": {"time_spans": None},
        "portfolioOptimization": {
            "algorithms": {
                "MarkowitzModel": {"gamma": .0},
                "MinimalVarianceModel": {"gamma": .0},
                "MaxSharpeModel": {"gamma": .0},
                "RiskParityModel": {}
            },
            "iterations": 30,
            "start": None,
            "t0": None
        },
        "alerts": {
            "w_ma_slow": 120,
            "w_ma_fast": 21,
            "w_sr_slow": 120,
            "w_sr_fast": 21,
            "sr_mult": 5.0
        }
    }
    _PTF_PLT_STYLE = {
        'Markowitz': (
            'plot',
            {
                'linestyle': '-', 'linewidth': 2., 'marker': '',
                'color': 'C0', 'label': 'EffFrontier'
            }
        ),
        'MaxSharpe': (
            'scatter',
            {'marker': 'o', 'color': 'C1', 'label': 'MaxSharpe'}
        ),
        'MinVariance': (
            'scatter',
            {'marker': 'o', 'color': 'C2', 'label': 'MinVariance'}
        ),
        'RiskParity': (
            'scatter',
            {'marker': 'o', 'color': 'C4', 'label': 'RiskParity'}
        ),
    }

    def __init__(self, data: ReportData, path: Optional[str] = None, **kwargs):
        super().__init__(data, path)
        self._time_spans = (
            Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M, Cn.DAYS_IN_1Y,
            2 * Cn.DAYS_IN_1Y, 3 * Cn.DAYS_IN_1Y, 5 * Cn.DAYS_IN_1Y
        )

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

    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """
        outputs = defaultdict(dict)
        for uid in self.uids:
            print(f'  > {uid}')
            try:
                asset = self._af.get(uid)
                if asset.type != 'Company':
                    msg = f'{uid} is not a company'
                    raise Ex.AssetTypeError(msg)

                res = Ut.AttributizedDict()
                self._calc_company(asset, res)
                self._calc_equity(asset, res)
                outputs[uid] = res

            except (RuntimeError, Ex.AssetTypeError) as ex:
                Ut.print_exc(ex)

        return outputs

    def _calc_equity(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'description', 'name', 'sector', 'industry',
                      'equity', 'currency', 'country')
        }

        # Relative path in results object
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('ME',), ('p_price',)
            )
        )
        res.img_prices = fig_rel[0]

        t0 = self._cal.t0

        # Prices: full history plot
        equity = self._af.get(asset.equity)
        prices = equity.prices
        v_p = prices.values
        dt_p = prices.index.values
        v_r = equity.returns.values

        start = self._cal.shift(t0, -2. * Cn.DAYS_IN_1Y, 'D')
        slc = Math.search_trim_pos(
            dt_p,
            start=start.asm8,
            end=t0.asm8
        )

        IO.TSPlot() \
            .lplot(0, prices[slc], label='Price') \
            .plot() \
            .save(fig_full[0]) \
            .close(True)

        # Last price
        last_price, idx = Math.last_valid_value(v_p, dt_p, t0.asm8)
        res.last_price = last_price
        res.last_price_date = str(dt_p[idx])[:10]

        # Statistics table and betas
        stats = np.empty((2, len(self._time_spans)))

        for i, span in enumerate(self._time_spans):
            start = self._cal.shift(t0, -span, 'D')
            slc_sp = Math.search_trim_pos(
                dt_p,
                start=start.asm8,
                end=t0.asm8
            )

            stats[0, i] = float(np.nanstd(v_r[slc_sp]))
            first_price = Math.next_valid_value(v_p[slc_sp])[0]
            stats[1, i] = last_price / first_price - 1.

        # Render dataframes
        df = pd.DataFrame(
            stats.T,
            index=self._time_spans,
            columns=('\u03C3', 'tot. return')
        )
        res.stats = df.style.format(
            formatter={
                '\u03C3': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

    def _calc_company(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        uid = asset.uid

        dcf_res = None
        try:
            dcf_res = DiscountedCashFlowModel(uid, **self._p) \
                .result(**self._p)
        except Exception as ex:
            Ut.print_exc(ex)

        ddm_res = None
        try:
            ddm_res = DividendDiscountModel(uid, **self._p) \
                .result(**self._p)
        except Exception as ex:
            Ut.print_exc(ex)

        # Render DDM
        if ddm_res is not None:
            res.has_ddm = True
            res.ccy = ddm_res.ccy
            res.last_price = ddm_res.last_price
            res.ret_zg = ddm_res.ret_no_growth * 100.
            res.ret_wg = ddm_res.ret_with_growth * 100.
            res.fair_value_no_growth = ddm_res.fair_value_no_growth
            res.fair_value_with_growth = ddm_res.fair_value_with_growth

            labels = ((ddm_res.uid,), ('DDM',), ('div',))
            fig_full, fig_rel = self._get_image_paths(labels)
            res.div_fig = fig_rel[0]

            # Save out figure
            IO.TSPlot(yl=('Dividend',)) \
                .lplot(0, ddm_res.div_ts, marker='o', label='historical') \
                .lplot(0, ddm_res.div_zg[0, :], ddm_res.div_zg[1, :],
                       marker='o', label='no growth') \
                .lplot(0, ddm_res.div_gwt[0, :], ddm_res.div_gwt[1, :],
                       marker='o', label='w/ growth') \
                .plot() \
                .save(fig_full[0]) \
                .close(True)
        else:
            res.has_ddm = False

        # Render DCF
        if dcf_res is not None:
            res.has_dcf = True
            res.ccy = dcf_res.ccy
            res.last_price = dcf_res.last_price
            res.fair_value = dcf_res.fair_value

            df = dcf_res.df
            df.index = df.index.strftime("%Y-%m-%d")
            res.df = df.T.style \
                .format("{:.2f}", **PD_STYLE_PROP) \
                .set_table_attributes('class="dataframe"') \
                .render()
        else:
            res.has_dcf = False