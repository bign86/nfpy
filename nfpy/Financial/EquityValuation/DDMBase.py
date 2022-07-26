
import nfpy.Assets as Ast
import nfpy.Financial as Fin
from nfpy.Tools import Exceptions as Ex

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


class DDMResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Dividend Model family. """


class DDMBase(BaseFundamentalModel):

    _RES_OBJ = DDMResult

    def __init__(self, uid: str, **kwargs):
        super().__init__(uid)

        self._df = Fin.DividendFactory(self._eq)
        self._rf = Fin.get_rf_glob()
        self._last_price = None

        self._check_applicability()

    def _calc_last_price(self) -> None:
        """ Returns the last price of the company's equity converted in the
            same currency as the company for consistency with the reported
            financial statements figures.
        """
        v, dt, _ = self._eq.last_price()
        cv_obj = Ast.get_fx_glob()\
            .get(self._eq.currency, self._asset.currency)
        self._last_price = v * cv_obj.get(dt)

    def _check_applicability(self) -> None:
        """ Check applicability of the DDM model to the equity. The presence
            and frequency of dividends is checked.
        """
        # We assume DDM cannot be used if dividends are NOT paid
        if not self._df.is_dividend_payer:
            raise Ex.MissingData(f'No dividends for {self._eq.uid}')

        # If the last dividend was outside the tolerance for the inferred
        # frequency, assume the dividend has been suspended
        if self._df.is_dividend_suspended:
            msg = f'Dividends for {self._uid} [{self._eq.uid}] appear to have been suspended'
            raise Ex.MissingData(msg)

    def _calc_freq(self) -> None:
        """ Calculates model frequency. """
        self._freq = self._df.frequency

    def _calc_drift(self) -> float:
        """ Calculate annualized equity and dividend drifts. """
        # Get dividends drift
        try:
            div_drift = self._df.annualized_drift
        except ValueError:
            div_drift = .0

        return div_drift

    def get_last_price(self) -> float:
        if not self._last_price:
            self._calc_last_price()
        return self._last_price
