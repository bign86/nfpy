#
# MADM Report
# Report class for the Market Asset Data Model
#

from nfpy.Calendar import get_calendar_glob
from nfpy.Financial.Models import MarketAssetsDataBaseModel
import nfpy.IO as IO

from .BaseReport import BaseReport


class ReportMADM(BaseReport):
    _M_OBJ = MarketAssetsDataBaseModel
    _M_LABEL = 'MADM'
    _IMG_LABELS = ['p_long', 'p_short']
    INPUT_QUESTIONS = ()

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        d = {'uid': self._uid}
        d.update(self._p)
        return d

    def _create_output(self, res):
        """ Create the final output. """
        # Create the image path
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.prices_long, res.prices_short = fig_rel_name
        full_name_long, full_name_short = fig_full_name

        p = res.prices

        # Slow plot
        start = get_calendar_glob().start.asm8

        div_pl = IO.PlotTS()
        div_pl.add(p)
        div_pl.add(res.ma_slow, color='C2', linewidth=1.5,
                   linestyle='--', label='MA {}'.format(res.w_slow))
        div_pl.line('h', res.sr_slow, (start, res.date.asm8), color='b',
                    linewidth=.5, linestyles='-')

        div_pl.plot()
        div_pl.save(full_name_long)
        div_pl.clf()

        # Fast plot
        try:
            w = self._p['w_plot_fast']
        except KeyError:
            w = 120
        start = get_calendar_glob().shift(res.date, w, 'D', fwd=False).asm8

        div_pl = IO.PlotTS()
        div_pl.add(p.loc[start:])
        div_pl.add(res.ma_fast[start:], color='C1', linewidth=1.5,
                   linestyle='--', label='MA {}'.format(res.w_fast))
        div_pl.add(res.ma_slow[start:], color='C2', linewidth=1.5,
                   linestyle='--', label='MA {}'.format(res.w_slow))
        div_pl.line('h', res.sr_fast, (start, res.date.asm8), color='k',
                    linewidth=.5, linestyles='--')

        div_pl.plot()
        div_pl.save(full_name_short)

        div_pl.close(True)

        return res
