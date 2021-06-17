#
# Portfolio Optimization Report
# Report class for the Portfolio Optimization Model
#

import numpy as np
import pandas as pd

import nfpy.Assets as Ast
from nfpy.Calendar import get_calendar_glob
import nfpy.IO as IO
import nfpy.Models as Mod
from nfpy.Tools import Utilities as Ut

from .BaseReport import BaseReport


class ResultReportOptimization(Ut.AttributizedDict):
    """ Report data for Jinja generated from single optimization results. """


class ReportPtfOptimization(BaseReport):
    _IMG_LABELS = ['_ptf_optimization_res']
    _M_LABEL = 'PtfOptimization'
    _PLT_STYLE = {
        'Markowitz': (
            'plot',
            {'linestyle': '-', 'linewidth': 2., 'marker': '',
             'color': 'C0', 'label': 'EffFrontier'}
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

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        t0 = get_calendar_glob().t0
        start = pd.Timestamp(year=(t0.year - 2), month=t0.month, day=t0.day)
        params = {'iterations': 50, 'start': start.asm8,
                  't0': t0.asm8, 'gamma': None}
        params.update(self._p)
        return params

    def _run(self):
        kwargs = self._init_input()

        # Calculate actual weights ex-cash positions
        ptf = Ast.get_af_glob().get(self._uid)
        idx = ptf.constituents_uids.index(ptf.currency)
        wgt = np.delete(ptf.weights.values[-1], idx)
        wgt /= np.sum(wgt)

        # Run optimizers
        oe = Mod.OptimizationEngine(self._uid, **kwargs)
        model_res = oe.result

        self._res = self._create_output(model_res, wgt)

    def _create_output(self, model_res: Mod.OptimizationEngineResult,
                       wgt: np.ndarray):
        """ Create the final output.

            Input:
                model_res [list]: list of optimizer results
                wgt [np.ndarray]: array of weights

            Output:
                res [ResultReportPtfOptimization]: result of the optimization
        """
        # Generate plot paths
        uid = self._uid
        fig_full_name, fig_rel_name = self._get_image_paths(uid)

        # Create result object
        res = ResultReportOptimization()
        res.var_ret_plot = fig_rel_name[0]
        res.uid = uid

        # Create plot
        div_pl = IO.PtfOptimizationPlot(x_zero=(.0,), y_zero=(.0,))

        # Process data
        models = ['Actual']
        weights = [wgt]
        for r in model_res.results:
            if r.success is False:
                continue

            model = r.model
            call, kw = self._PLT_STYLE[model]
            div_pl.add(0, call, r, **kw)

            if model == 'Markowitz':
                continue

            models.extend([model, model + '_delta'])
            model_wgt = r.weights[0]
            weights.extend([model_wgt, model_wgt / wgt - 1.])

        # Save out figure
        div_pl.plot()
        div_pl.save(fig_full_name[0])
        div_pl.close(True)

        # Create correlation matrix
        corr_df = pd.DataFrame(model_res.corr, index=model_res.uids,
                               columns=model_res.uids)
        res.corr = corr_df.style.format('{:,.0%}') \
            .set_table_attributes('class="matrix"') \
            .render()
        # .background_gradient(cmap='RdYlGn', axis=None) \

        # Create results table
        wgt_df = pd.DataFrame(np.vstack(weights).T,
                              index=model_res.uids,
                              columns=models)
        res.weights = wgt_df.style.format('{:,.1%}') \
            .set_table_attributes('class="dataframe"') \
            .render()

        return res
