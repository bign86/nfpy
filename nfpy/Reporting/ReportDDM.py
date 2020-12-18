#
# DDM Report
# Report class for the Dividend Discount Model
#

from copy import deepcopy

from nfpy.Financial.DividendDiscountModel import DividendDiscountModel, DDMResult
from nfpy.Handlers.Plotting import PlotTS
from nfpy.Reporting.BaseReport import BaseReport


class ReportDDM(BaseReport):
    _M_OBJ = DividendDiscountModel
    _M_LABEL = 'DDM'
    _IMG_LABELS = ['div']
    INPUT_QUESTIONS = (
        ('date', 'Insert date of calculation (default None): ',
         {'idesc': 'datetime', 'optional': True}),
        ('past_horizon', 'Insert length of past horizon (default 5): ',
         {'idesc': 'int', 'optional': True}),
        ('future_proj', 'Insert length of future projection (default 3): ',
         {'idesc': 'int', 'optional': True}),
        ('div_conf', 'Insert confidence for determination of dividend frequency (default .1): ',
         {'idesc': 'float', 'optional': True}),
        ('susp_conf', 'Insert confidence for determination of dividend suspension (default 1.): ',
         {'idesc': 'float', 'optional': True}),
        ('d_rate', 'Insert discounting rate (default Risk Free): ',
         {'idesc': 'float', 'optional': True}),
    )

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        p = deepcopy(self._p)
        p.update({'company': self._uid})
        return p

    def _create_output(self, res) -> DDMResult:
        """ Create the final output. """
        # Create the image path
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.div_fig = fig_rel_name[0]

        # Save out figure
        div_pl = PlotTS(yl='Dividend')
        div_pl.add(res.div_ts, marker='o', label='historical')
        div_pl.add(res.div_zg[0, :], res.div_zg[1, :], marker='o', label='no growth')
        div_pl.add(res.div_gwt[0, :], res.div_gwt[1, :], marker='o', label='w/ growth')
        div_pl.plot()
        div_pl.save(fig_full_name[0])
        div_pl.clf()

        div_pl.close(True)

        return res
