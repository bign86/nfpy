#
# MADM Report
# Report class for the Market Asset Data Model
#

from nfpy.Financial.MarketAssetsDataBaseModel import MarketAssetsDataBaseModel
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Handlers.Plotting import PlotTS
from nfpy.Reporting.BaseReport import BaseReport


class ReportMADM(BaseReport):
    _M_OBJ = MarketAssetsDataBaseModel
    _M_LABEL = 'MADM'
    _IMG_LABELS = ['p_long', 'p_short']
    INPUT_QUESTIONS = ()

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        return {'uid': self._uid}

    def _create_output(self, res):
        """ Create the final output. """
        # Create the image path
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.prices_long, res.prices_short = fig_rel_name
        full_name_long, full_name_short = fig_full_name

        # Save out figure
        start = get_calendar_glob().shift(res.date, 120, 'D', fwd=False)
        p = res.prices

        div_pl = PlotTS()
        div_pl.add(p)
        div_pl.plot()
        div_pl.save(full_name_long)
        div_pl.clf()

        div_pl = PlotTS()
        div_pl.add(p.loc[start:])
        div_pl.plot()
        div_pl.save(full_name_short)

        div_pl.close(True)

        return res
