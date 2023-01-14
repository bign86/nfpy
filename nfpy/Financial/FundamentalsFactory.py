#
# Fundamentals Factory
# Class to handle the calculations of fundamental quantities
#

import numpy as np
from typing import (Callable, Optional)

from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)


class FundamentalsFactory(object):
    __slots__ = ['_comp', '_cnst', '_labels', '_df_a', '_df_q', '_df_t']

    def __init__(self, company):
        self._comp = company
        self._cnst = company.cnsts_df
        self._labels = company.constituents_uids

        dfa = company.cnsts_df.loc[('A', slice(None)), :]
        dfa.index = dfa.index.droplevel(0)
        self._df_a = dfa
        dfq = company.cnsts_df.loc[('Q', slice(None)), :]
        dfq.index = dfq.index.droplevel(0)
        self._df_q = dfq
        dft = company.cnsts_df.loc[('TTM', slice(None)), :]
        dft.index = dft.index.droplevel(0)
        self._df_t = dft

    def _financial(self, code: str, freq: str,
                   callb: Optional[Callable] = None,
                   cb_args: Optional[tuple] = None) \
            -> tuple[np.ndarray, np.ndarray]:
        """ Base function to return fundamental data. """
        df = self._df_a if freq == 'A' else self._df_q
        res = np.array([np.nan] * len(df))

        if code in self._labels:
            v = df[code].values
            mask = np.isnan(res)
            res[mask] = v[mask]

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
            _, v = callb(*cb_args)
            mask = np.isnan(res)
            res[mask] = v[mask]

        if np.isnan(res).all():
            raise Ex.MissingData(f'FundamentalsFactory(): {code}|{freq} not found for {self._comp.uid}')

        return df.index.values, res

    def book_value(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('QTLE', freq)

    def book_value_ps(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0TBVP', freq, self._book_value_ps, (freq,))

    def _book_value_ps(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Book Value Per Share as:
                Total Equity / Total Shares Outstanding
                (Total Book Value / Total Shares Outstanding)
        """
        idx, n = self._financial('QTLE', freq)
        _, d = self.total_shares(freq)
        return idx, n / d

    def cash_interest_paid(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('SCIP', freq)

    def common_shares(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('QTCO', freq, self._total_shares, (freq,))

    def _common_shares(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Total Shares Outstanding as:
                Common Shares + Preferred Shares
        """
        idx, n = self._financial('0TSOS', freq)
        try:
            _, m = self._financial('QTPO', freq)
        except KeyError:
            m = 0
        return idx, n - m

    def cost_of_debt(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0CODB', freq, self._cost_of_debt, (freq,))

    def _cost_of_debt(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return the cost of debt as:
                Interest Expenses / Total Liabilities
        """
        idx, n = self.interest_expenses(freq)
        _, d = self._financial('LTLL', freq)
        return idx, n / d

    def eps(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0BEPS', freq, self._eps, (freq,))

    def _eps(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Cash EPS as:
                1. Operating Cash Flow / Shares Outstanding
                2. (Net Income AT + Depr&Amort * (1 - Tax Rate)) / Shares Outstanding
                   Note that as per now the Tax Rate is assumed 0
        """
        idx, d = self.total_shares(freq)
        try:
            _, n = self._financial('OTLO', freq)
        except KeyError as ke:
            Ut.print_wrn(Warning(ke.__str__()))
            _, v = self._financial('TIAT', freq)
            _, n = self._financial('SDPR', freq)
            ret = v + n / d
        else:
            ret = n / d
        return idx, ret

    def eps_cash(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0CEPS', freq, self._eps, (freq,))

    def eps_diluted_normalized(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('VDES', freq)

    def ebit(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('SOPI', freq, self._ebit, (freq,))

    def _ebit(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Operating Income as:
                1. Revenue - Operating Expenses
                2. Net Income AT + Interest Expenses + Tax Provision
        """
        try:
            idx, n = self._financial('RTLR', freq)
            _, m = self._financial('ETOE', freq)
            d = n - m
        except KeyError as ke:
            Ut.print_wrn(Warning(ke.__str__()))
            idx, n = self._financial('TIAT', freq)
            _, m = self._financial('STIE', freq)
            _, k = self.income_tax_paid(freq)
            d = n + m + k
        return idx, d

    def fcfe(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0FCFE', freq, self._fcfe, (freq,))

    def _fcfe(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Free Cash Flow to Equity as:
                Operating Cash Flow - Capital Expenditures + Net Borrowings
        """
        idx, n = self._financial('OTLO', freq)
        _, m = self._financial('SCEX', freq)
        _, b = self._financial('FPRD', freq)
        return idx, n - m + b

    def fcff(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0FCFF', freq, self._fcff, (freq,))

    def _fcff(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Free Cash Flow to the Firm as:
                Operating Cash Flow + Interest Paid Net of Tax - Capital Expenditures
        """
        idx, n = self._financial('OTLO', freq)
        _, m = self._financial('SCEX', freq)
        _, i = self.interest_expenses(freq)
        _, t = self.tax_rate(freq)
        return idx, n - m + i * (1. - t)

    def get_index(self, freq: str) -> np.ndarray:
        df = self._df_a if freq == 'A' else self._df_q
        return df.index.values

    def income_before_taxes(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('EIBT', freq)

    def income_tax_paid(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        # return self._financial('TTAX', freq, self._income_tax_paid, (freq,))
        return self._financial('TTAX', freq)

    # FIXME: this calculation doesn't work. There must be some other adjustment.
    def _income_tax_paid(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Provision for Income Tax as:
                Net Income Before Taxes - Net Income After Taxes
        """
        idx, n = self._financial('EIBT', freq)
        _, d = self._financial('NINC', freq)
        return idx, n - d

    def interest_expenses(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('STIE', freq, self._interest_expenses, (freq,))

    def _interest_expenses(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Interest Expenses as:
                Operating Income - Net Income AT - Taxes Provision
        """
        idx, n = self.ebit(freq)
        _, m = self._financial('TIAT', freq)
        _, k = self.income_tax_paid(freq)
        return idx, n - m - k

    def net_diluted_income(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('SDNI', freq, self.net_income, (freq,))

    def net_income(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('NINC', freq)

    def roe(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0ROE', freq, self._roe, (freq,))

    def _roe(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return ROE as:
                Net Income / Total Equity
        """
        idx, n = self._financial('NINC', freq)
        _, d = self._financial('QTLE', freq)
        return idx, n / d

    def tax_rate(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0TXR', freq, self._tax_rate, (freq,))

    def _tax_rate(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Tax Rate as:
                Income Tax Paid / Income Before Taxes
        """
        idx, n = self.income_tax_paid(freq)
        _, d = self.income_before_taxes(freq)
        return idx, n / d

    def total_asset(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('ATOT', freq)

    def total_debt(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('STLD', freq, self._total_debt, (freq,))

    def _total_debt(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Total Debt as:
                Capital Leases + Total Long Term Debt + Short Term Debt
        """
        idx, n = self._financial('LLTD', freq)
        _, m = self._financial('LTTD', freq)
        # _, k = self._financial('LSTD', freq)
        return idx, n + m  # + k

    def total_equity(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('QTLE', freq)

    def total_liabilities(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('LTLL', freq)

    def total_revenues(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('RTLR', freq)

    def total_shares(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        return self._financial('0TSOS', freq, self._total_shares, (freq,))

    def _total_shares(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
        """ Return Total Shares Outstanding as:
                Common Shares + Preferred Shares
        """
        idx, n = self._financial('QTCO', freq)
        try:
            _, m = self._financial('QTPO', freq)
        except KeyError:
            m = 0
        return idx, n + m

    ######################

    # TODO
    # def fcff(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
    #     return self._financial('0FCFF', freq, self._fcff, (freq,))
    #
    # def _fcff(self, freq: str) -> tuple[np.ndarray, np.ndarray]:
    #     """ Return Free Cash Flow to Firm as:
    #             1. Net Income + Dep&Amor + Interest Expenses(1 – Tax Rate)
    #                 – Capital Expenditures + Change Working Capital
    #     """
    #     # https://www.wallstreetmojo.com/free-cash-flow-firm-fcff/
    #     labels = ['TIAT', 'SDPR', 'STIE', 'SOCF', 'SCEX']
    #     if all(f in self._labels for f in labels):
    #         idx, res = self._financial('TIAT', freq)
    #         for lb in labels[1:]:
    #             _, d = self._financial(lb, freq)
    #             mask = np.isnan(res)
    #             res[mask] = d[mask]
    #             res[~mask] += d[~mask]
    #     else:
    #         raise Ex.MissingData(f'FCFF [0FCFF] for {self._comp.uid} not found')
    #     return idx, res
