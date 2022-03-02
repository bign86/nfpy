#
# Portfolio Report
# Report class for the Portfolio Data
#

from collections import defaultdict
import numpy as np
import pandas as pd
from typing import (Any, Optional)

from nfpy.Assets import TyAsset
import nfpy.Financial.Portfolio as Ptf
import nfpy.IO as IO
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


class ReportPortfolio(BaseReport):
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
            Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M,
            Cn.DAYS_IN_1Y  # , 2 * Cn.DAYS_IN_1Y, 5 * Cn.DAYS_IN_1Y
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
        t0 = self._cal.t0
        start = pd.Timestamp(year=(t0.year - 2), month=t0.month, day=t0.day)

        opt_p = self._p.get('portfolioOptimization', {})
        opt_p.update({'start': start.asm8, 't0': t0.asm8})

        self._p['portfolioOptimization'] = opt_p

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
        for uid in self.uids:
            print(f'  > {uid}')
            try:
                asset = self._af.get(uid)
                if asset.type != 'Portfolio':
                    msg = f'{uid} is not a portfolio'
                    raise Ex.AssetTypeError(msg)
                self._init_input()

                res = Ut.AttributizedDict()
                pe = Ptf.PortfolioEngine(asset)
                self._calc_ptf(asset, res, pe)
                self._calc_optimization(asset, res, pe)
                outputs[uid] = res

            except (RuntimeError, Ex.AssetTypeError) as ex:
                Ut.print_exc(ex)

        return outputs

    def _calc_ptf(self, asset: TyAsset, res: Ut.AttributizedDict,
                  pe: Ptf.PortfolioEngine) -> None:
        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'description', 'name', 'currency',
                      'inception_date', 'benchmark', 'num_constituents')
        }

        # Relative path in results object
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('ME',), ('p_price',)
            )
        )
        res.img_value_hist = fig_rel[0]

        t0 = self._cal.t0

        # Prices: full history plot
        dt_p, v_p = pe.total_value
        _, v_r = pe.returns

        IO.TSPlot() \
            .lplot(0, dt_p, v_p, label='Value') \
            .plot() \
            .save(fig_full[0]) \
            .close(True)

        # Last price
        last_price, idx = Math.last_valid_value(v_p, dt_p, t0.asm8)
        res.last_price = last_price
        res.last_price_date = str(dt_p[idx])[:10]

        # Statistics table and betas
        stats = np.empty((3, len(self._time_spans)))
        for i, span in enumerate(self._time_spans):
            start = self._cal.shift(t0, -span, 'D')
            slc_sp = Math.search_trim_pos(
                dt_p,
                start=start.asm8,
                end=t0.asm8
            )

            first_price = Math.next_valid_value(v_p[slc_sp])[0]
            tot_ret = last_price / first_price - 1.

            stats[0, i] = float(np.nanstd(v_r[slc_sp]))
            stats[1, i] = Math.compound(tot_ret, Cn.BDAYS_IN_1Y / span)
            stats[2, i] = tot_ret

        # Render dataframes
        df = pd.DataFrame(
            stats.T,
            index=self._time_spans,
            columns=('\u03C3', 'yearly return', 'tot. return')
        )
        res.stats = df.style.format(
            formatter={
                '\u03C3': '{:,.1%}'.format,
                'yearly return': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Portfolio summary
        summary = pe.summary()
        res.tot_value = summary['tot_value'],

        merged = pd.merge(
            summary['constituents_data'],
            pd.DataFrame(
                pe.weights[-1],
                index=asset.constituents_uids,
                columns=['weights']
            ),
            left_on='uid',
            right_index=True
        )
        res.cnsts_data = merged.style.format(
            formatter={
                'alp': '{:,.2f}'.format,
                'cost (FX)': '{:,.2f}'.format,
                f'value ({asset.currency})': '{:,.2f}'.format,
                'quantity': '{:,.0f}'.format,
                'weights': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP) \
            .hide_index() \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Dividends received
        res.div_ttm = pe.dividends_received_ttm()
        res.div_history = pe.dividends_received_yearly()

    def _calc_optimization(self, asset: TyAsset, res: Ut.AttributizedDict,
                           pe: Ptf.PortfolioEngine) -> None:
        # Plot portfolio data
        fig_full, fig_rel = self._get_image_paths(
            ((asset.uid,), ('PtfOpt',), ('ptf_opt_res',))
        )
        res.var_ret_plot = fig_rel[0]

        idx = asset.constituents_uids.index(asset.currency)
        wgt = np.delete(pe.weights[-1], idx)
        wgt /= np.sum(wgt)

        # Portfolio optimization
        oe = Ptf.OptimizationEngine(
            asset.uid,
            **self._p['portfolioOptimization']
        ).result

        # Create plot
        pl = IO.PtfOptimizationPlot(x_zero=(.0,), y_zero=(.0,))

        # Process data
        models = ['Actual']
        weights = [wgt]
        for r in oe.results:
            if r.success is False:
                continue

            model = r.model
            call, kw = self._PTF_PLT_STYLE[model]
            pl.add(0, call, r, **kw)

            if model == 'Markowitz':
                continue

            models.extend([model, model + '_delta'])
            model_wgt = r.weights[0]
            weights.extend([model_wgt, model_wgt / wgt - 1.])

        # Save out figure
        pl.plot() \
            .save(fig_full[0]) \
            .close(True)

        # Create correlation matrix
        res.corr = pd.DataFrame(oe.corr, index=oe.uids, columns=oe.uids) \
            .style \
            .format('{:,.0%}') \
            .set_table_attributes('class="matrix"') \
            .render()

        # Create results table
        wgt_df = pd.DataFrame(np.vstack(weights).T,
                              index=oe.uids,
                              columns=models)
        res.weights = wgt_df.style \
            .format('{:,.1%}') \
            .set_table_attributes('class="dataframe"') \
            .render()
