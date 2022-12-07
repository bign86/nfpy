#
# Configurations for Downloads
#


#
# Yahoo
#

YahooFinancialsConf = ['ticker', 'freq', 'currency', 'statement', 'date', 'code', 'value']
YahooFinancialsMapping = {
    'INC':
        {
            'researchDevelopment': ('ERAD', 0, 1.),
            'effectOfAccountingCharges': ('SFEE', 0, 1.),
            'incomeBeforeTax': ('EIBT', 0, 1.),
            'minorityInterest': ('CMIN', 0, 1.),
            'netIncome': ('NINC', 0, 1.),
            'sellingGeneralAdministrative': ('SSGA', 0, 1.),
            'grossProfit': ('SGRP', 0, 1.),
            'ebit': ('', 0, 1.),
            'operatingIncome': ('', 0, 1.),  # not SOPI!
            'otherOperatingExpenses': ('SOOE', 0, 1.),
            'interestExpense': ('STIE', 0, 1.),
            'extraordinaryItems': ('STXI', 0, 1.),
            'nonRecurring': ('', 0, 1.),
            'otherItems': ('SONT', 0, 1.),
            'incomeTaxExpense': ('TTAX', 0, 1.),
            'totalRevenue': ('RTLR', 0, 1.),
            'totalOperatingExpenses': ('ETOE', 0, 1.),
            'costOfRevenue': ('SCOR', 0, 1.),
            'totalOtherIncomeExpenseNet': ('SOOE', 0, 1.),
            'discontinuedOperations': ('', 0, 1.),
            'netIncomeFromContinuingOps': ('TIAT', 0, 1.),
            'netIncomeApplicableToCommonShares': ('XNIC', 0, 1.)
        },
    'BAL':
        {
            'intangibleAssets': ('AINT', 0, 1.),
            'totalLiab': ('LTLL', 0, 1.),
            'totalStockholderEquity': ('QTLE', 0, 1.),
            'deferredLongTermLiab': ('', 0, 1.),
            'otherCurrentLiab': ('SOCL', 0, 1.),
            'totalAssets': ('ATOT', 0, 1.),
            'commonStock': ('', 0, 1.),
            'otherCurrentAssets': ('SOCA', 0, 1.),
            'retainedEarnings': ('QRED', 0, 1.),
            'minorityInterest': ('CMIN', 0, 1.),
            'otherLiab': ('SLTL', 0, 1.),
            'goodWill': ('AGWI', 0, 1.),
            'treasuryStock': ('QTSC', 0, 1.),
            'otherAssets': ('SOAT', 0, 1.),
            'cash': ('ACAE', 0, 1.),
            'totalCurrentLiabilities': ('LTCL', 0, 1.),
            'deferredLongTermAssetCharges': ('', 0, 1.),
            'shortLongTermDebt': ('', 0, 1.),
            'otherStockholderEquity': ('SOTE', 0, 1.),
            'propertyPlantEquipment': ('APPN', 0, 1.),
            'totalCurrentAssets': ('ATCA', 0, 1.),
            'longTermInvestments': ('SINV', 0, 1.),
            'netTangibleAssets': ('0ANTA', 0, 1.),
            'shortTermInvestments': ('ASTI', 0, 1.),
            'netReceivables': ('ATRC', 0, 1.),
            'longTermDebt': ('LLTD', 0, 1.),
            'inventory': ('AITL', 0, 1.),
            'accountsPayable': ('LAPB', 0, 1.),
            'capitalSurplus': ('', 0, 1.)
        },
    'CAS':
        {
            # NOTE: netIncome is renamed CFnetIncome to avoid clashing with Income statement
            'changeToLiabilities': ('0SCLB', 0, 1.),
            'totalCashflowsFromInvestingActivities': ('ITLI', 0, 1.),
            'repurchaseOfStock': ('', 0, 1.),
            'netBorrowings': ('FPRD', 0, 1.),
            'totalCashFromFinancingActivities': ('FTLF', 0, 1.),
            'changeToOperatingActivities': ('', 0, 1.),
            'netIncome': ('ONET', 0, 1.),
            'changeInCash': ('SNCC', 0, 1.),
            'effectOfExchangeRate': ('SFEE', 0, 1.),
            'totalCashFromOperatingActivities': ('OTLO', 0, 1.),
            'depreciation': ('SDED', 0, 1.),
            'otherCashflowsFromInvestingActivities': ('SICF', 0, 1.),
            'dividendsPaid': ('FCDP', 0, 1.),
            'changeToInventory': ('0SCIN', 0, 1.),
            'changeToAccountReceivables': ('0SCAR', 0, 1.),
            'otherCashflowsFromFinancingActivities': ('SFCF', 0, 1.),
            'changeToNetincome': ('0SCNI', 0, 1.),
            'capitalExpenditures': ('SCEX', 0, 1.),
            'investments': ('', 0, 1.),
            'issuanceOfStock': ('SFEE', 0, 1.)
        },
    'TS':
        {
            'Amortization': ('', 0, 1.),
            'AmortizationOfIntangiblesIncomeStatement': ('', 0, 1.),
            'AverageDilutionEarnings': ('', 0, 1.),
            'BasicAccountingChange': ('', 0, 1.),
            'BasicAverageShares': ('QTCO', 0, 1.),
            'BasicContinuousOperations': ('', 0, 1.),
            'BasicDiscontinuousOperations': ('', 0, 1.),
            'BasicEPS': ('0BEPS', 0, 1.),
            'BasicEPSOtherGainsLosses': ('', 0, 1.),
            'BasicExtraordinary': ('', 0, 1.),
            'CededPremiums': ('', 0, 1.),
            'ContinuingAndDiscontinuedBasicEPS': ('', 0, 1.),
            'ContinuingAndDiscontinuedDilutedEPS': ('', 0, 1.),
            'CostOfRevenue': ('', 0, 1.),
            'CreditCard': ('', 0, 1.),
            'CreditLossesProvision': ('', 0, 1.),
            'DDACostofRevenue': ('', 0, 1.),
            'DepletionIncomeStatement': ('', 0, 1.),
            'DepreciationAmortizationDepletionIncomeStatement': ('', 0, 1.),
            'DepreciationAndAmortizationInIncomeStatement': ('', 0, 1.),
            'DepreciationIncomeStatement': ('', 0, 1.),
            'DilutedAccountingChange': ('', 0, 1.),
            'DilutedAverageShares': ('SDWS', 0, 1.),
            'DilutedContinuousOperations': ('', 0, 1.),
            'DilutedDiscontinuousOperations': ('', 0, 1.),
            'DilutedEPS': ('0DEPS', 0, 1.),
            'DilutedEPSOtherGainsLosses': ('', 0, 1.),
            'DilutedExtraordinary': ('', 0, 1.),
            'DilutedNIAvailtoComStockholders': ('', 0, 1.),
            'DividendIncome': ('', 0, 1.),
            'DividendPerShare': ('', 0, 1.),
            'earnings': ('', 0, 1.),
            'EarningsFromEquityInterest': ('', 0, 1.),
            'EarningsFromEquityInterestNetOfTax': ('', 0, 1.),
            'EBIT': ('', 0, 1.),
            'EBITDA': ('', 0, 1.),
            'EPSactual': ('', 0, 1.),
            'EPSestimate': ('', 0, 1.),
            'Equipment': ('', 0, 1.),
            'ExciseTaxes': ('', 0, 1.),
            'ExplorationDevelopmentAndMineralPropertyLeaseExpenses': ('', 0, 1.),
            'FeesandCommissionExpense': ('', 0, 1.),
            'FeesandCommissionIncome': ('', 0, 1.),
            'FeesAndCommissions': ('', 0, 1.),
            'Fuel': ('', 0, 1.),
            'FuelAndPurchasePower': ('', 0, 1.),
            'ForeignExchangeTradingGains': ('', 0, 1.),
            'GainLossonSaleofAssets': ('', 0, 1.),
            'GainOnSaleOfBusiness': ('', 0, 1.),
            'GainonSaleofInvestmentProperty': ('', 0, 1.),
            'GainonSaleofLoans': ('', 0, 1.),
            'GainOnSaleOfPPE': ('', 0, 1.),
            'GainOnSaleOfSecurity': ('', 0, 1.),
            'GeneralAndAdministrativeExpense': ('', 0, 1.),
            'GrossPremiumsWritten': ('', 0, 1.),
            'GrossProfit': ('', 0, 1.),
            'ImpairmentOfCapitalAssets': ('', 0, 1.),
            'IncreaseDecreaseInNetUnearnedPremiumReserves': ('', 0, 1.),
            'IncomefromAssociatesandOtherParticipatingInterests': ('', 0, 1.),
            'InsuranceAndClaims': ('', 0, 1.),
            'InterestExpense': ('', 0, 1.),
            'InterestExpenseForDeposit': ('', 0, 1.),
            'InterestExpenseForFederalFundsSoldAndSecuritiesPurchaseUnderAgreementsToResell': ('', 0, 1.),
            'InterestExpenseForLongTermDebtAndCapitalSecurities': ('', 0, 1.),
            'InterestExpenseForShortTermDebt': ('', 0, 1.),
            'InterestExpenseNonOperating': ('', 0, 1.),
            'InterestIncome': ('', 0, 1.),
            'InterestIncomeAfterProvisionForLoanLoss': ('', 0, 1.),
            'InterestIncomeFromDeposits': ('', 0, 1.),
            'InterestIncomeFromFederalFundsSoldAndSecuritiesPurchaseUnderAgreementsToResell': ('', 0, 1.),
            'InterestIncomeFromLeases': ('', 0, 1.),
            'InterestIncomeFromLoans': ('', 0, 1.),
            'InterestIncomeFromLoansAndLease': ('', 0, 1.),
            'InterestIncomeFromSecurities': ('', 0, 1.),
            'InterestIncomeNonOperating': ('', 0, 1.),
            'InvestmentBankingProfit': ('', 0, 1.),
            'LossonExtinguishmentofDebt': ('', 0, 1.),
            'MaintenanceAndRepairs': ('', 0, 1.),
            'MinorityInterests': ('', 0, 1.),
            'NetIncome': ('NINC', 1, 1.),
            'NetIncomeCommonStockholders': ('', 0, 1.),
            'NetIncomeContinuousOperations': ('TIAT', 1, 1.),
            'NetIncomeDiscontinuousOperations': ('', 0, 1.),
            'NetIncomeExtraordinary': ('', 0, 1.),
            'NetIncomeFromContinuingAndDiscontinuedOperation': ('', 0, 1.),
            'NetIncomeFromContinuingOperationNetMinorityInterest': ('', 0, 1.),
            'NetIncomeFromTaxLossCarryforward': ('', 0, 1.),
            'NetIncomeIncludingNoncontrollingInterests': ('', 0, 1.),
            'NetInterestIncome': ('', 0, 1.),
            'NetInvestmentIncome': ('', 0, 1.),
            'NetNonOperatingInterestIncomeExpense': ('', 0, 1.),
            'NetOccupancyExpense': ('', 0, 1.),
            'NetPolicyholderBenefitsAndClaims': ('', 0, 1.),
            'NetPremiumsWritten': ('', 0, 1.),
            'NetRealizedGainLossOnInvestments': ('', 0, 1.),
            'NonInterestExpense': ('', 0, 1.),
            'NonInterestIncome': ('', 0, 1.),
            'NormalizedBasicEPS': ('0NBEP', 0, 1.),
            'NormalizedDilutedEPS': ('VDES', 0, 1.),
            'NormalizedEBITDA': ('0NEBD', 0, 1.),
            'NormalizedIncome': ('', 0, 1.),
            'OccupancyAndEquipment': ('', 0, 1.),
            'OperatingExpense': ('', 0, 1.),
            'OperatingIncome': ('', 0, 1.),
            'OperatingRevenue': ('', 0, 1.),
            'OperationAndMaintenance': ('', 0, 1.),
            'OtherCostofRevenue': ('', 0, 1.),
            'OtherCustomerServices': ('', 0, 1.),
            'OtherGandA': ('', 0, 1.),
            'OtherIncomeExpense': ('', 0, 1.),
            'OtherInterestExpense': ('', 0, 1.),
            'OtherInterestIncome': ('', 0, 1.),
            'OtherNonInterestExpense': ('', 0, 1.),
            'OtherNonInterestIncome': ('', 0, 1.),
            'OtherNonOperatingIncomeExpenses': ('', 0, 1.),
            'OtherOperatingExpenses': ('', 0, 1.),
            'OtherSpecialCharges': ('', 0, 1.),
            'OtherTaxes': ('', 0, 1.),
            'OtherunderPreferredStockDividend': ('', 0, 1.),
            'PolicyAcquisitionExpense': ('', 0, 1.),
            'PreferredStockDividends': ('', 0, 1.),
            'PretaxIncome': ('EIBT', 1, 1.),
            'ProfessionalExpenseAndContractServicesExpense': ('', 0, 1.),
            'ProvisionForDoubtfulAccounts': ('', 0, 1.),
            'ReconciledCostOfRevenue': ('', 0, 1.),
            'ReconciledDepreciation': ('', 0, 1.),
            'RentAndLandingFees': ('', 0, 1.),
            'RentandLandingFeesCostofRevenue': ('', 0, 1.),
            'RentExpenseSupplemental': ('', 0, 1.),
            'ReportedNormalizedBasicEPS': ('', 0, 1.),
            'ReportedNormalizedDilutedEPS': ('', 0, 1.),
            'ResearchAndDevelopment': ('', 0, 1.),
            'RestructuringAndMergernAcquisition': ('', 0, 1.),
            'SalariesAndWages': ('', 0, 1.),
            'SecuritiesActivities': ('', 0, 1.),
            'SecuritiesAmortization': ('', 0, 1.),
            'SellingAndMarketingExpense': ('', 0, 1.),
            'SellingGeneralAndAdministration': ('', 0, 1.),
            'ServiceChargeOnDepositorAccounts': ('', 0, 1.),
            'SpecialIncomeCharges': ('', 0, 1.),
            'TaxEffectOfUnusualItems': ('', 0, 1.),
            'TaxLossCarryforwardBasicEPS': ('', 0, 1.),
            'TaxLossCarryforwardDilutedEPS': ('', 0, 1.),
            'TaxProvision': ('', 0, 1.),
            'TaxRateForCalcs': ('0TXR', 0, 1.),
            'TotalExpenses': ('', 0, 1.),
            'TotalMoneyMarketInvestments': ('', 0, 1.),
            'TotalOperatingIncomeAsReported': ('SOPI', 0, 1.),
            'TotalOtherFinanceCost': ('', 0, 1.),
            'TotalPremiumsEarned': ('', 0, 1.),
            'TotalRevenue': ('', 0, 1.),
            'TotalUnusualItems': ('', 0, 1.),
            'TotalUnusualItemsExcludingGoodwill': ('', 0, 1.),
            'TradingGainLoss': ('', 0, 1.),
            'TrustFeesbyCommissions': ('', 0, 1.),
            'WriteOff': ('', 0, 1.)
        }
}

YahooHistPricesConf = ["date", "open", "high", "low", "close", "adj_close", "volume"]

YahooHistDividendsConf = ["date", "value"]

YahooHistSplitsConf = ["date", "value"]

#
# ECB
#

ECBSeriesConf = ["date", "value", "notes"]

#
# Investing
#

InvestingSeriesConf = ["date", "price", "open", "high", "low", "volume"]

InvestingFinancialsConf = ['ticker', 'freq', 'date', 'currency', 'statement', 'code', 'value']

InvestingFinancialsMapping = {
    'CAS':
        {
            'Net Income/Starting Line': ('ONET', 0, None),
            'Cash From Operating Activities': ('OTLO', 0, None),
            'Depreciation/Depletion': ('SDED', 0, None),
            'Amortization': ('SAMT', 0, None),
            'Deferred Taxes': ('OBDT', 0, None),
            'Non-Cash Items': ('SNCI', 0, None),
            'Cash Receipts': ('0XCR', 0, None),
            'Cash Payments': ('0XCP', 0, None),
            'Cash Taxes Paid': ('SCTP', 0, None),
            'Cash Interest Paid': ('SCIP', 0, None),
            'Changes in Working Capital': ('SOCF', 0, None),
            'Cash From Investing Activities': ('ITLI', 0, None),
            'Capital Expenditures': ('SCEX', 0, None),
            'Other Investing Cash Flow Items, Total': ('SICF', 0, None),
            'Cash From Financing Activities': ('FTLF', 0, None),
            'Financing Cash Flow Items': ('SFCF', 0, None),
            'Total Cash Dividends Paid': ('FCDP', 0, None),
            'Issuance (Retirement) of Stock, Net': ('FPSS', 0, None),
            'Issuance (Retirement) of Debt, Net': ('FPRD', 0, None),
            'Foreign Exchange Effects': ('SFEE', 0, None),
            'Net Change in Cash': ('SNCC', 0, None),
            'Beginning Cash Balance': ('0BCB', 0, None),
            'Ending Cash Balance': ('0ECB', 0, None),
            'Free Cash Flow': ('0FCFE', 0, None),
            'Free Cash Flow Growth': ('0FCFG', 0, None),
            'Free Cash Flow Yield': ('0FCFY', 0, None)
        },
    'BAL':
        {
            'Total Current Assets': ('ATCA', 0, None),
            'Cash & Due from Banks': ('ACDB', 0, None),
            'Other Earning Assets, Total': ('SOEA', 0, None),
            'Net Loans': ('ANTL', 0, None),
            'Cash and Short Term Investments': ('SCSI', 0, None),
            'Cash': ('ACSH', 0, None),
            'Total Deposits': ('LDBT', 0, None),
            'Cash & Equivalents': ('ACAE', 0, None),
            'Short Term Investments': ('ASTI', 0, None),
            'Total Receivables, Net': ('ATRC', 0, None),
            'Accounts Receivables - Trade, Net': ('AACR', 0, None),
            'Total Inventory': ('AITL', 0, None),
            'Prepaid Expenses': ('APPY', 0, None),
            'Other Current Assets, Total': ('SOCA', 0, None),
            'Total Assets': ('ATOT', 0, None),
            'Property/Plant/Equipment, Total - Net': ('APPN', 0, None),
            'Property/Plant/Equipment, Total - Gross': ('APTC', 0, None),
            'Accumulated Depreciation, Total': ('ADEP', 0, None),
            'Goodwill, Net': ('AGWI', 0, None),
            'Intangibles, Net': ('AINT', 0, None),
            'Long Term Investments': ('SINV', 0, None),
            'Note Receivable - Long Term': ('ALTR', 0, None),
            'Other Long Term Assets, Total': ('SOLA', 0, None),
            'Other Assets, Total': ('SOAT', 0, None),
            'Total Current Liabilities': ('LTCL', 0, None),
            'Other Bearing Liabilities, Total': ('SOBL', 0, None),
            'Accounts Payable': ('LAPB', 0, None),
            'Payable/Accrued': ('LPBA', 0, None),
            'Accrued Expenses': ('LAEX', 0, None),
            'Notes Payable/Short Term Debt': ('LSTD', 0, None),
            'Current Port. of LT Debt/Capital Leases': ('LCLD', 0, None),
            'Other Current liabilities, Total': ('SOCL', 0, None),
            'Total Liabilities': ('LTLL', 0, None),
            'Total Short Term Borrowings': ('LSTB', 0, None),
            'Total Long Term Debt': ('LTTD', 0, None),
            'Long Term Debt': ('LLTD', 0, None),
            'Capital Lease Obligations': ('LCLO', 0, None),
            'Deferred Income Tax': ('SBDT', 0, None),
            'Minority Interest': ('LMIN', 0, None),
            'Other Liabilities, Total': ('SLTL', 0, None),
            'Total Equity': ('QTLE', 0, None),
            'Redeemable Preferred Stock, Total': ('SRPR', 0, None),
            'Preferred Stock - Non Redeemable, Net': ('SPRS', 0, None),
            'Common Stock, Total': ('SCMS', 0, None),
            'Additional Paid-In Capital': ('QPIC', 0, None),
            'Retained Earnings (Accumulated Deficit)': ('QRED', 0, None),
            'Treasury Stock - Common': ('QTSC', 0, None),
            'ESOP Debt Guarantee': ('QEDG', 0, None),
            'Unrealized Gain (Loss)': ('QUGL', 0, None),
            'Other Equity, Total': ('SOTE', 0, None),
            "Total Liabilities & Shareholders' Equity": ('QTEL', 0, None),
            'Total Common Shares Outstanding': ('QTCO', 0, None),
            'Total Preferred Shares Outstanding': ('QTPO', 0, None),
        },
    'INC':
        {
            'Net Interest Income': ('ENII', 0, None),
            'Interest Income, Bank': ('SIIB', 0, None),
            'Total Interest Expense': ('STIE', 0, None),
            'Loan Loss Provision': ('ELLP', 0, None),
            'Net Interest Income After Loan Loss Provision': ('SIAP', 0, None),
            'Non-Interest Income, Bank': ('SNII', 0, None),
            'Non-Interest Expense, Bank': ('SNIE', 0, None),
            'Total Revenue': ('RTLR', 0, None),
            'Revenue': ('SREV', 0, None),
            'Other Revenue, Total': ('SORE', 0, None),
            'Cost of Revenue, Total': ('SCOR', 0, None),
            'Gross Profit': ('SGRP', 0, None),
            'Total Operating Expenses': ('ETOE', 0, None),
            'Selling/General/Admin. Expenses, Total': ('SSGA', 0, None),
            'Research & Development': ('ERAD', 0, None),
            'Depreciation / Amortization': ('SDPR', 0, None),
            'Interest Expense (Income) - Net Operating': ('SINN', 0, None),
            'Unusual Expense (Income)': ('SUIE', 0, None),
            'Other Operating Expenses, Total': ('SOOE', 0, None),
            'Operating Income': ('SOPI', 0, None),
            'Interest Income (Expense), Net Non-Operating': ('SNIN', 0, None),
            'Gain (Loss) on Sale of Assets': ('NGLA', 0, None),
            'Other, Net': ('SONT', 0, None),
            'Net Income Before Taxes': ('EIBT', 0, None),
            'Provision for Income Taxes': ('TTAX', 0, None),
            'Net Income After Taxes': ('TIAT', 0, None),
            'Minority Interest': ('CMIN', 0, None),
            'Equity In Affiliates': ('CEIA', 0, None),
            'U.S GAAP Adjustment': ('CGAP', 0, None),
            'Net Income Before Extraordinary Items': ('NIBX', 0, None),
            'Total Extraordinary Items': ('STXI', 0, None),
            'Net Income': ('NINC', 0, None),
            'Total Adjustments to Net Income': ('SANI', 0, None),
            'Income Available to Common Excluding Extraordinary Items': ('CIAC', 0, None),
            'Dilution Adjustment': ('SDAJ', 0, None),
            'Diluted Net Income': ('SDNI', 0, None),
            'Diluted Weighted Average Shares': ('SDWS', 0, None),
            'Diluted EPS Excluding Extraordinary Items': ('SDBF', 0, 1.),  # divide
            'DPS - Common Stock Primary Issue': ('DDPS1', 0, 1.),  # divide
            'Diluted Normalized EPS': ('VDES', 0, 1.)  # divide
        }
}

#
# Interactive Brokers
#

IBFinancialsConf = ['ticker', 'freq', 'date', 'currency', 'statement', 'code', 'value']

IBFinancialsMapping = {
    'BAL': {
        'AACR': ('AACR', 0, 1e6),
        'ACAE': ('ACAE', 0, 1e6),
        'ACDB': ('ACDB', 0, 1e6),
        'ACSH': ('ACSH', 0, 1e6),
        'ADEP': ('ADEP', 0, 1e6),
        'ADPA': ('ADPA', 0, 1e6),
        'AGWI': ('AGWI', 0, 1e6),
        'AINT': ('AINT', 0, 1e6),
        'AITL': ('AITL', 0, 1e6),
        'ALTR': ('ALTR', 0, 1e6),
        'ANTL': ('ANTL', 0, 1e6),
        'APPN': ('APPN', 0, 1e6),
        'APPY': ('APPY', 0, 1e6),
        'APRE': ('APRE', 0, 1e6),
        'APTC': ('APTC', 0, 1e6),
        'ASTI': ('ASTI', 0, 1e6),
        'ATCA': ('ATCA', 0, 1e6),
        'ATOT': ('ATOT', 0, 1e6),
        'ATRC': ('ATRC', 0, 1e6),
        'LAEX': ('LAEX', 0, 1e6),
        'LAPB': ('LAPB', 0, 1e6),
        'LCLD': ('LCLD', 0, 1e6),
        'LCLO': ('LCLO', 0, 1e6),
        'LDBT': ('LDBT', 0, 1e6),
        'LLTD': ('LLTD', 0, 1e6),
        'LMIN': ('LMIN', 0, 1e6),
        'LPBA': ('LPBA', 0, 1e6),
        'LSTB': ('LSTB', 0, 1e6),
        'LSTD': ('LSTD', 0, 1e6),
        'LTCL': ('LTCL', 0, 1e6),
        'LTLL': ('LTLL', 0, 1e6),
        'LTTD': ('LTTD', 0, 1e6),
        'QEDG': ('QEDG', 0, 1e6),
        'QPIC': ('QPIC', 0, 1e6),
        'QRED': ('QRED', 0, 1e6),
        'QTCO': ('QTCO', 0, 1e6),
        'QTEL': ('QTEL', 0, 1e6),
        'QTLE': ('QTLE', 0, 1e6),
        'QTPO': ('QTPO', 0, 1e6),
        'QTSC': ('QTSC', 0, 1e6),
        'QUGL': ('QUGL', 0, 1e6),
        'SBDT': ('SBDT', 0, 1e6),
        'SCMS': ('SCMS', 0, 1e6),
        'SCSI': ('SCSI', 0, 1e6),
        'SINV': ('SINV', 0, 1e6),
        'SLTL': ('SLTL', 0, 1e6),
        'SOAT': ('SOAT', 0, 1e6),
        'SOBL': ('SOBL', 0, 1e6),
        'SOCA': ('SOCA', 0, 1e6),
        'SOCL': ('SOCL', 0, 1e6),
        'SOEA': ('SOEA', 0, 1e6),
        'SOLA': ('SOLA', 0, 1e6),
        'SOTE': ('SOTE', 0, 1e6),
        'SPOL': ('SPOL', 0, 1e6),
        'SPRS': ('SPRS', 0, 1e6),
        'SRPR': ('SRPR', 0, 1e6),
        'STBP': ('STBP', 0, 1e6),
        'STLD': ('STLD', 0, 1e6),
        'SUPN': ('SUPN', 0, 1e6),
    },
    'CAS': {
        'FCDP': ('FCDP', 0, 1e6),
        'FPRD': ('FPRD', 0, 1e6),
        'FPSS': ('FPSS', 0, 1e6),
        'FTLF': ('FTLF', 0, 1e6),
        'ITLI': ('ITLI', 0, 1e6),
        'OBDT': ('OBDT', 0, 1e6),
        'ONET': ('ONET', 0, 1e6),
        'OTLO': ('OTLO', 0, 1e6),
        'SAMT': ('SAMT', 0, 1e6),
        'SCEX': ('SCEX', 0, 1e6),
        'SCIP': ('SCIP', 0, 1e6),
        'SCTP': ('SCTP', 0, 1e6),
        'SDED': ('SDED', 0, 1e6),
        'SFCF': ('SFCF', 0, 1e6),
        'SFEE': ('SFEE', 0, 1e6),
        'SICF': ('SICF', 0, 1e6),
        'SNCC': ('SNCC', 0, 1e6),
        'SNCI': ('SNCI', 0, 1e6),
        'SOCF': ('SOCF', 0, 1e6),
    },
    'INC': {
        'CEIA': ('CEIA', 0, 1e6),
        'CGAP': ('CGAP', 0, 1e6),
        'CIAC': ('CIAC', 0, 1e6),
        'CMIN': ('CMIN', 0, 1e6),
        'DDPS1': ('DDPS1', 0, 1.),
        'EDOE': ('EDOE', 0, 1e6),
        'EIBT': ('EIBT', 0, 1e6),
        'ELLP': ('ELLP', 0, 1e6),
        'ENII': ('ENII', 0, 1e6),
        'ERAD': ('ERAD', 0, 1e6),
        'ETOE': ('ETOE', 0, 1e6),
        'NAFC': ('NAFC', 0, 1e6),
        'NGLA': ('NGLA', 0, 1e6),
        'NIBX': ('NIBX', 0, 1e6),
        'NINC': ('NINC', 0, 1e6),
        'RNII': ('RNII', 0, 1e6),
        'RRGL': ('RRGL', 0, 1e6),
        'RTLR': ('RTLR', 0, 1e6),
        'SANI': ('SANI', 0, 1e6),
        'SCOR': ('SCOR', 0, 1e6),
        'SDAJ': ('SDAJ', 0, 1e6),
        'SDBF': ('SDBF', 0, 1e6),
        'SDNI': ('SDNI', 0, 1e6),
        'SDPR': ('SDPR', 0, 1e6),
        'SDWS': ('SDWS', 0, 1e6),
        'SGRP': ('SGRP', 0, 1e6),
        'SIAP': ('SIAP', 0, 1e6),
        'SIIB': ('SIIB', 0, 1e6),
        'SINN': ('SINN', 0, 1e6),
        'SLBA': ('SLBA', 0, 1e6),
        'SNIE': ('SNIE', 0, 1e6),
        'SNII': ('SNII', 0, 1e6),
        'SNIN': ('SNIN', 0, 1e6),
        'SONT': ('SONT', 0, 1e6),
        'SOOE': ('SOOE', 0, 1e6),
        'SOPI': ('SOPI', 0, 1e6),
        'SORE': ('SORE', 0, 1e6),
        'SPRE': ('SPRE', 0, 1e6),
        'SREV': ('SREV', 0, 1e6),
        'SSGA': ('SSGA', 0, 1e6),
        'STIE': ('STIE', 0, 1e6),
        'STXI': ('STXI', 0, 1e6),
        'SUIE': ('SUIE', 0, 1e6),
        'TIAT': ('TIAT', 0, 1e6),
        'TTAX': ('TTAX', 0, 1e6),
        'VDES': ('VDES', 0, 1e6),
        'XNIC': ('XNIC', 0, 1e6),
    }
}

#
# Nasdaq
#

NasdaqDividendsConf = ['date', 'type', 'amount', 'declaration_date', 'record_date', 'payment_date']
NasdaqPricesConf = ['date', 'close', 'volume', 'open', 'high', 'low']

#
# OECD
#

OECDSeriesConf = [
    "location", "country", "transact_code", "transact", "measure_code",
    "measure", "frequency_code", "frequency", "date_code", "date", "unit_code",
    "unit", "powercode_code", "powercode", "value"
]

#
# Borsa Italiana
#

BorsaItalianaDividendsConf = [
    'ticker', 'type', 'dps_bod', 'dps_agm', 'currency',
    'ex_date', 'payment', 'agm', 'notice'
]
