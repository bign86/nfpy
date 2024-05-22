#
# Fundamentals Factory
# Class to handle the calculations of fundamental quantities
#

import numpy as np
from typing import (Callable, Optional)

import nfpy.IO.Utilities as Ut
from nfpy.Tools import Exceptions as Ex


class FundamentalsFactory(object):
    __slots__ = ['_comp', '_cnst', '_labels', '_df_a', '_df_q', '_df_t']

    def __init__(self, company):
        self._comp = company
        self._cnst = company.financials
        self._labels = company.constituents_uids

        dfa = self._cnst.loc[('A', slice(None)), :]
        dfa.index = dfa.index.droplevel(0)
        self._df_a = dfa
        dfq = self._cnst.loc[('Q', slice(None)), :]
        dfq.index = dfq.index.droplevel(0)
        self._df_q = dfq
        # We introduce a try as not every company as TTM data
        try:
            dft = self._cnst.loc[('TTM', slice(None)), :]
            dft.index = dft.index.droplevel(0)
            self._df_t = dft
        except KeyError:
            self._df_t = None

    def _financial(self, code: str, freq: str,
                   level: int = 0,
                   callb: Optional[Callable] = None,
                   cb_args: Optional[tuple] = None) \
            -> tuple[np.ndarray, np.ndarray]:
        """ Base function to return fundamental data.
            The callback must be able to accept the <level> argument to keep
            track of the depth of the calculation. The function may be recursive
            as _financial() can be given as callback.
        """
        df = self._df_a if freq == 'A' else self._df_q
        res = np.array([np.nan] * len(df), dtype=float)

        if code in self._labels:
            v = df[code].values
            # mask = np.isnan(res)
            res[:] = v[:]

        if not np.isnan(res).any():
            return df.index.values, res

        # FIXME: we need to match the indices of the previous array with
        #        the one of the _df_t that is going to be monthly.
        #        Until this is done, we comment out this part.
        # v = self._df_t[code].values
        # if not np.isnan(res).all():
        #     mask = np.isnan(res)
        #     res[mask] = v[mask]
        #
        # if not np.isnan(res).any():
        #     return df.index.values, res

        if callb:
            _, v = callb(*cb_args, level=level+1)
            mask = np.isnan(res)
            res[mask] = v[mask]

        if level == 0:
            if np.isnan(res).all():
                raise Ex.MissingData(f'FundamentalsFactory(): {code}|{freq} not found for {self._comp.uid}')

        return df.index.values, res

    def book_value(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('SKHLEQ', freq, level)

    def book_value_ps(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('BKVLSH', freq, level, self._book_value_ps, (freq,))

    # TODO: Check formula e total_shares()
    def _book_value_ps(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Book Value Per Share as:
                Total Equity / Total Shares Outstanding
                (Total Book Value / Total Shares Outstanding)
        """
        idx, n = self._financial('SKHLEQ', freq, level)
        _, d = self.total_shares(freq, level)
        return idx, n / d

    # FIXME: this is gone
    def cash_interest_paid__(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('SCIP', freq, level)

    def capex(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return the Capital Expenditures """
        return self._financial('CAPEXP', freq, level, self._financial, ('CAPEXR', freq))

    def cash_dividends_paid(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return the total of Cash Dividends Paid """
        return self._financial('CHDIVP', freq, level)

    def cfo(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return the Operating Cash FLow. If missing return the Operating Cash
            Flow using the Total Operating Cash Flow.
        """
        return self._financial('OPCHFW', freq, level, self._financial, ('CFWOPA', freq))

    def _cfo(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return the Operating Cash Flow using the Total Operating Cash Flow """
        return self._financial('CFWOPA', freq, level)

    def common_shares(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('ODSHNM', freq, level, self._common_shares, (freq,))

    def _common_shares(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Total Common Shares as:
                Shares Issued - Preferred Shares - Treasury Shares
        """
        idx, shi = self._financial('SHRISS', freq, level)
        _, prs = self._financial('PRSHNM', freq, level)
        _, trs = self._financial('TRSHNM', freq, level)
        # If Shares Issued is absent we keep the nan
        np.nan_to_num(prs, copy=False, nan=0.0)
        np.nan_to_num(trs, copy=False, nan=0.0)
        return idx, shi - prs - trs

    def cost_of_debt(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        # FIXME: find a code for this
        return self._financial('0CODB', freq, level, self._cost_of_debt, (freq,))

    def _cost_of_debt(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return the cost of debt as:
                Interest Expenses / Total Liabilities
        """
        idx, n = self.interest_expenses(freq, level)
        _, d = self._financial('TOLIAB', freq, level)
        return idx, n / d

    def eps(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('BASEPS', freq, level, self._eps, (freq,))

    def _eps(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Cash EPS as:
                1. Operating Cash Flow / Shares Outstanding
                2. (Net Income AT + Depr&Amort * (1 - Tax Rate)) / Shares Outstanding
                   Note that as per now the Tax Rate is assumed 0
        """
        idx, d = self.total_shares(freq, level)
        try:
            _, n = self._financial('CFWOPA', freq, level)
        except KeyError as ke:
            Ut.print_wrn(Warning(ke.__str__()))
            _, v = self._financial('NICCST', freq, level)
            _, n = self._financial('DPAMIS', freq, level)
            ret = v + n / d
        else:
            ret = n / d
        return idx, ret

    # FIXME: this is gone
    def eps_cash__(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0CEPS', freq, level, self._eps, (freq,))

    def eps_diluted_normalized(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('NMDEPS', freq, level)

    def ebit(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('OPINCM', freq, level, self._ebit, (freq,))

    def _ebit(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Operating Income as:
                1. Revenue - Operating Expenses
                2. Net Income AT + Interest Expenses + Tax Provision
        """
        try:
            idx, n = self._financial('TOREVN', freq, level)
            _, m = self._financial('TOTEXP', freq, level)
            d = n - m
        except KeyError as ke:
            Ut.print_wrn(Warning(ke.__str__()))
            idx, n = self._financial('NICCST', freq, level)
            _, m = self._financial('INTEXP', freq, level)
            _, k = self.income_tax_paid(freq, level)
            d = n + m + k
        return idx, d

    # FIXME: this is gone
    def fcfe__(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0FCFE', freq, level, self._fcfe, (freq,))

    def _fcfe(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Free Cash Flow to Equity as:
                Operating Cash Flow - Capital Expenditures + Net Borrowings
        """
        idx, n = self._financial('CFWOPA', freq, level)
        _, m = self._financial('CAPEXP', freq, level)
        _, b = self._financial('NISDBT', freq, level)
        return idx, n - m + b

    def fcff(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('FRCHFL', freq, level, self._fcff, (freq,))

    def _fcff(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Free Cash Flow to the Firm as:
                Operating Cash Flow - Capital Expenditures
            The calculation above is consistent with the data reported by Yahoo.
            Other providers may calculate the Operating Cash Flow differently.
        """
        idx, cfo = self.cfo(freq, level)
        _, cx = self.capex(freq, level)
        return idx, cfo + cx

    def get_index(self, freq: str, level: int = 0) -> np.ndarray:
        df = self._df_a if freq == 'A' else self._df_q
        return df.index.values

    def income_before_taxes(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('PTXINC', freq, level)

    def income_tax_paid(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        # return self._financial('TXPROV', freq, self._income_tax_paid, (freq,))
        return self._financial('TXPROV', freq, level)

    # FIXME: this calculation doesn't work. There must be some other adjustment.
    def _income_tax_paid(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Provision for Income Tax as:
                Net Income Before Taxes - Net Income After Taxes
        """
        idx, n = self._financial('PTXINC', freq, level)
        _, d = self._financial('NETINC', freq, level)
        return idx, n - d

    def interest_expenses(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('INTEXP', freq, level, self._interest_expenses, (freq,))

    def _interest_expenses(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Interest Expenses as:
                Operating Income - Net Income AT - Taxes Provision
        """
        idx, n = self.ebit(freq, level)
        _, m = self._financial('NICCST', freq, level)
        _, k = self.income_tax_paid(freq, level)
        return idx, n - m - k

    def net_diluted_income(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('DLNIAC', freq, level, self.net_income, (freq,))

    def net_income(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('NETINC', freq, level)

    def roe(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('ROEQTY', freq, level, self._roe, (freq,))

    def _roe(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return ROE as:
                Net Income / Total Equity
        """
        idx, n = self._financial('NETINC', freq, level)
        _, d = self._financial('SKHLEQ', freq, level)
        return idx, n / d

    def tax_rate(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('TXRTCA', freq, level, self._tax_rate, (freq,))

    def _tax_rate(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Tax Rate as:
                Income Tax Paid / Income Before Taxes
        """
        idx, n = self.income_tax_paid(freq, level)
        _, d = self.income_before_taxes(freq, level)
        return idx, n / d

    def total_asset(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('TOTAST', freq, level)

    def total_debt(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('TOTDBT', freq, level, self._total_debt, (freq,))

    def _total_debt(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Total Debt as:
                Capital Leases + Total Long Term Debt + Short Term Debt
        """
        idx, lto = self._financial('LTCLOB', freq, level)
        _, ltd = self._financial('LTDEBT', freq, level)
        _, std = self._financial('STDBIS', freq, level)
        np.nan_to_num(lto, copy=False, nan=0.0)
        np.nan_to_num(ltd, copy=False, nan=0.0)
        np.nan_to_num(std, copy=False, nan=0.0)
        return idx, lto + ltd + std

    def total_equity(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('TOTEMI', freq, level)

    def total_liabilities(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('TOLIAB', freq, level)

    def total_revenues(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('TOREVN', freq, level)

    def total_shares(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('SHRISS', freq, level, self._total_shares, (freq,))

    def _total_shares(self, freq: str, level: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """ Return Total Shares Outstanding as:
                Common Shares + Preferred Shares + Treasury Shares
        """
        idx, n = self._financial('ODSHNM', freq, level)
        _, m = self._financial('PRSHNM', freq, level)
        _, k = self._financial('TRSHNM', freq, level)
        return idx, n + m + k
