#
# Portfolio Optimization Report
# Report class for the Portfolio Optimization Model
#

import numpy as np
import pandas as pd

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
import nfpy.Financial as Fin
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

from .BaseReport import BaseReport


class ResultReportOptimization(Ut.AttributizedDict):
    """ Report data for Jinja generated from single optimization results. """


class ReportPtfOptimization(BaseReport):
    _IMG_LABELS = ['_ptf_optimization_res']
    _M_LABEL = 'PtfOptimization'
    _PLT_STYLE = {
        'Markowitz': {'linestyle': '-', 'linewidth': 2., 'marker': '',
                      'color': 'C0', 'label': 'EffFrontier'},
        'MaxSharpe': {'marker': 'o', 'color': 'C1', 'label': 'MaxSharpe'},
        'MinVariance': {'marker': 'o', 'color': 'C2', 'label': 'MinVariance'},
        'RiskParity': {'marker': 'o', 'color': 'C4', 'label': 'RiskParity'}
    }

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        t0 = get_calendar_glob().t0
        start = pd.Timestamp(year=(t0.year - 1), month=t0.month, day=t0.day)
        params = {'iterations': 50, 'start': start.asm8,
                  't0': t0.asm8, 'gamma': None}
        params.update(self._p)
        return params

    def _run(self):
        kwargs = self._init_input()

        # Run optimizers
        oe = Fin.OptimizationEngine(self._uid, **kwargs)
        model_res = oe.result

        # Handlers
        af, fx = get_af_glob(), Fin.get_fx_glob()

        # Calculate actual weights ex-cash positions
        ptf = af.get(self._uid)
        weights = ptf.weights
        idx = [i for i, u in enumerate(weights.columns)
               if not fx.is_ccy(u)]
        wgt = weights.values[-1][idx]
        wgt = wgt / np.sum(wgt)

        self._res = self._create_output(model_res, wgt)

    def _create_output(self, model_res: Fin.ResultOptimization,
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
        div_pl = IO.PlotPortfolioOptimization(y_zero=.0)

        # Process data
        models = ['Actual']
        weights = [wgt]
        for r in model_res.results:
            model = r.model
            if r.success is False:
                continue

            kw = self._PLT_STYLE[model]
            div_pl.add(r, **kw)

            if model == 'Markowitz':
                continue

            models.extend([model, 'delta%'])
            weights.extend([r.weights, r.weights / wgt - 1.])

        wgt_table = np.vstack(weights)
        res.weights = pd.DataFrame(wgt_table.T,
                                   index=model_res.uids,
                                   columns=models)

        # Save out figure
        div_pl.plot()
        div_pl.save(fig_full_name[0])
        div_pl.close(True)

        return res
