#
# Fundamentals Factory class
# Class to handle the calculations of fundamental quantities
#

import pandas as pd
from typing import Callable

from nfpy.Tools import Exceptions as Ex


class FundamentalsFactory(object):

    def __init__(self, company):
        self._comp = company
        self._cnst = company.constituents

    def _financial(self, code: str, freq: str,
                   callb: Callable = None) -> pd.Series:
        """ Base function to return fundamental data. """
        tpl = (freq, code)
        try:
            d = self._comp.constituents[tpl]
            d.name = code
            return d
        except KeyError as ke:
            if not callb:
                raise ke
            else:
                d = callb(freq)
                self._comp.constituents[tpl] = d
                self._comp.constituents_uids.append(tpl)
                return d

    def get_index(self, freq: str) -> pd.Series:
        return self._comp.constituents[(freq, 'ATOT')].index

    def net_income(self, freq: str) -> pd.Series:
        return self._financial('NINC', freq)

    def income_before_taxes(self, freq: str) -> pd.Series:
        return self._financial('EIBT', freq)

    def income_tax_paid(self, freq: str) -> pd.Series:
        return self._financial('TTAX', freq, self._calc_tax_paid)

    def tot_revenues(self, freq: str) -> pd.Series:
        return self._financial('RTLR', freq)

    def tot_debt(self, freq: str) -> pd.Series:
        return self._financial('STLD', freq, self._calc_tot_debt)

    def tot_asset(self, freq: str) -> pd.Series:
        return self._financial('ATOT', freq)

    def ebit(self, freq: str) -> pd.Series:
        return self._financial('SOPI', freq, self._calc_ebit)

    def total_shares(self, freq: str) -> pd.Series:
        return self._financial('0TSOS', freq, self._calc_total_shares)

    def cash_eps(self, freq: str) -> pd.Series:
        return self._financial('0CEPS', freq, self._calc_cash_eps)

    def fcf(self, freq: str) -> pd.Series:
        return self._financial('0FCFE', freq, self._calc_fcf)

    def interest_expenses(self, freq: str) -> pd.Series:
        return self._financial('STIE', freq, self._calc_int_exp)

    def cost_of_debt(self, freq: str) -> pd.Series:
        return self._financial('0CODB', freq, self._calc_cost_debt)

    def cash_interest_paid(self, freq: str) -> pd.Series:
        return self._financial('SCIP', freq)

    # TODO
    def fcff(self, freq: str) -> pd.Series:
        return self._financial('0FCFF', freq, self._calc_fcff)

    ######################

    def _calc_tax_paid(self, freq: str) -> pd.Series:
        """ Return Provision for Income Tax as:
                Net Income Before Taxes - Net Income After Taxes
        """
        c = self._cnst
        d = c[(freq, 'EIBT')] - c[(freq, 'TIAT')]
        d.name = 'TTAX'
        return d

    def _calc_tot_debt(self, freq: str) -> pd.Series:
        """ Return Total Debt as:
                Capital Leases + Total Long Term Debt + Short Term Debt
        """
        c = self._cnst
        d = c[(freq, 'LCLD')] + c[(freq, 'LTTD')] + c[(freq, 'LSTD')]
        d.name = 'STLD'
        return d

    def _calc_ebit(self, freq: str) -> pd.Series:
        """ Return Operating Income as:
                1. Revenue - Operating Expenses
                2. Net Income AT + Interest Expenses + Tax Provision
        """
        c = self._cnst
        try:
            d = c[(freq, 'RTLR')] - c[(freq, 'ETOE')]
        except KeyError as ke:
            print(ke)
            d = c[(freq, 'TIAT')] + c[(freq, 'STIE')] + self.income_tax_paid(freq)
        d.name = 'SOPI'
        return d

    def _calc_total_shares(self, freq: str) -> pd.Series:
        """ Return Total Shares Outstanding as:
                Common Shares + Preferred Shares
        """
        c = self._cnst
        d = c[(freq, 'QTCO')].fillna(method='ffill', inplace=False)
        try:
            d = d + c[(freq, 'QTPO')].fillna(method='ffill', inplace=False)
        except KeyError:
            pass
        d.name = '0TSOS'
        return d

    def _calc_cash_eps(self, freq: str) -> pd.Series:
        """ Return Cash EPS as:
                1. Operating Cash Flow / Shares Outstanding
                2. (Net Income AT + Depr&Amort * (1 - Tax Rate)) / Shares Outstanding
                   Note that as per now the Tax Rate is assumed 0
        """
        c = self._cnst
        try:
            d = c[(freq, 'OTLO')] / self.total_shares(freq)
        except KeyError as ke:
            print(ke)
            d = (c[(freq, 'TIAT')] + c[(freq, 'SDPR')]) / self.total_shares(freq)
        d.name = '0CEPS'
        return d

    def _calc_fcf(self, freq: str) -> pd.Series:
        """ Return Free Cash Flow as:
                Operating Cash Flow - Capital Expenditures
        """
        c = self._cnst
        d = c[(freq, 'OTLO')] + c[(freq, 'SCEX')]
        d.name = '0FCFE'
        return d

    def _calc_int_exp(self, freq: str) -> pd.Series:
        """ Return Interest Expenses as:
                Operating Income - Net Income AT - Taxes Provision
        """
        c = self._cnst
        d = self.ebit(freq) - c[(freq, 'TIAT')] - self.income_tax_paid(freq)
        d.name = 'STIE'
        return d

    def _calc_cost_debt(self, freq: str) -> pd.Series:
        """ Return the cost of debt as:
                Interest Expenses / Total Liabilities
        """
        c = self._cnst
        d = self.interest_expenses(freq) / c[(freq, 'LTLL')]
        d.name = '0CODB'
        return d

    # TODO
    def _calc_fcff(self, freq: str) -> pd.Series:
        """ Return Free Cash Flow to Firm as:
                1. Net Income + Dep&Amor + Interest Expenses(1 – Tax Rate)
                    – Capital Expenditures + Change Working Capital
        """
        # https://www.wallstreetmojo.com/free-cash-flow-firm-fcff/
        cnst = self._comp.constituents
        labels = ['TIAT', 'SDPR', 'STIE', 'SOCF', 'SCEX']
        if all((freq, f) in self._comp.constituents_uids for f in labels):
            d = cnst[(freq, 'TIAT')] + cnst[(freq, 'SDPR')] + \
                cnst[(freq, 'STIE')] + cnst[(freq, 'SCEX')] + \
                cnst[(freq, 'SOCF')]
        else:
            raise Ex.MissingData(f'FCFF [0FCFF] for {self._comp.uid} not found')
        d.name = '0FCFF'
        return d
