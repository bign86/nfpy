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
            'researchDevelopment': 'ERAD',
            'effectOfAccountingCharges': 'SFEE',
            'incomeBeforeTax': 'EIBT',
            'minorityInterest': 'CMIN',
            'netIncome': 'NINC',
            'sellingGeneralAdministrative': 'SSGA',
            'grossProfit': 'SGRP',
            'ebit': '',
            'operatingIncome': 'SOPI',
            'otherOperatingExpenses': 'SOOE',
            'interestExpense': 'STIE',
            'extraordinaryItems': 'STXI',
            'nonRecurring': '',
            'otherItems': 'SONT',
            'incomeTaxExpense': 'TTAX',
            'totalRevenue': 'RTLR',
            'totalOperatingExpenses': 'ETOE',
            'costOfRevenue': 'SCOR',
            'totalOtherIncomeExpenseNet': 'SOOE',
            'discontinuedOperations': '',
            'netIncomeFromContinuingOps': 'NINC',
            'netIncomeApplicableToCommonShares': 'XNIC'
        },
    'BAL':
        {
            'intangibleAssets': 'AINT',
            'totalLiab': 'LTLL',
            'totalStockholderEquity': 'QTLE',
            'deferredLongTermLiab': '',
            'otherCurrentLiab': 'SOCL',
            'totalAssets': 'ATOT',
            'commonStock': '',
            'otherCurrentAssets': 'SOCA',
            'retainedEarnings': 'QRED',
            'otherLiab': 'SLTL',
            'goodWill': 'AGWI',
            'treasuryStock': 'QTSC',
            'otherAssets': 'SOAT',
            'cash': 'ACAE',
            'totalCurrentLiabilities': 'LTCL',
            'deferredLongTermAssetCharges': '',
            'shortLongTermDebt': '',
            'otherStockholderEquity': 'SOTE',
            'propertyPlantEquipment': 'APPN',
            'totalCurrentAssets': 'ATCA',
            'longTermInvestments': 'SINV',
            'netTangibleAssets': '0ANTA',
            'shortTermInvestments': 'ASTI',
            'netReceivables': 'ATRC',
            'longTermDebt': 'LLTD',
            'inventory': 'AITL',
            'accountsPayable': 'LAPB',
            'capitalSurplus': ''
        },
    'CAS':
        {
            # NOTE: netIncome is renamed CFnetIncome to avoid clashing with Income statement
            'changeToLiabilities': '0SCLB',
            'totalCashflowsFromInvestingActivities': 'ITLI',
            'repurchaseOfStock': '',
            'netBorrowings': 'FPRD',
            'totalCashFromFinancingActivities': 'FTLF',
            'changeToOperatingActivities': '',
            'netIncome': 'ONET',
            'changeInCash': 'SNCC',
            'effectOfExchangeRate': 'SFEE',
            'totalCashFromOperatingActivities': 'OTLO',
            'depreciation': 'SDED',
            'otherCashflowsFromInvestingActivities': 'SICF',
            'dividendsPaid': 'FCDP',
            'changeToInventory': '0SCIN',
            'changeToAccountReceivables': '0SCAR',
            'otherCashflowsFromFinancingActivities': 'SFCF',
            'changeToNetincome': '0SCNI',
            'capitalExpenditures': 'SCEX',
            'investments': '',
            'issuanceOfStock': 'SFEE'
        },
    'TS':
        {
            'earnings': '',
            'EPSactual': '',
            'EPSestimate': '',
            'InterestExpense': '',
            'DilutedNIAvailtoComStockholders': '',
            'NetIncome': '',
            'PretaxIncome': '',
            'TotalUnusualItems': '',
            'NetIncomeExtraordinary': '',
            'InterestIncome': '',
            'WriteOff': '',
            'TaxRateForCalcs': '',
            'EBIT': '',
            'TotalExpenses': '',
            'NetIncomeCommonStockholders': '',
            'DepreciationAmortizationDepletionIncomeStatement': '',
            'ImpairmentOfCapitalAssets': '',
            'NetIncomeFromContinuingAndDiscontinuedOperation': '',
            'OtherNonOperatingIncomeExpenses': '',
            'SellingGeneralAndAdministration': '',
            'GeneralAndAdministrativeExpense': '',
            'OtherGandA': '',
            'SpecialIncomeCharges': '',
            'NormalizedEBITDA': '',
            'ReconciledCostOfRevenue': '',
            'InterestIncomeNonOperating': '',
            'EBITDA': '',
            'ReconciledDepreciation': '',
            'NetIncomeFromContinuingOperationNetMinorityInterest': '',
            'NetNonOperatingInterestIncomeExpense': '',
            'NetInterestIncome': '',
            'OtherIncomeExpense': '',
            'OperatingRevenue': '',
            'PreferredStockDividends': '',
            'GrossProfit': '',
            'DilutedAverageShares': '',
            'OperatingIncome': '',
            'SalariesAndWages': '',
            'TaxProvision': '',
            'CostOfRevenue': '',
            'ResearchAndDevelopment': '',
            'InterestExpenseNonOperating': '',
            'DilutedEPS': '',
            'TotalUnusualItemsExcludingGoodwill': '',
            'TotalRevenue': '',
            'NetIncomeIncludingNoncontrollingInterests': '',
            'EarningsFromEquityInterest': '',
            'TotalOperatingIncomeAsReported': '',
            'SellingAndMarketingExpense': '',
            'BasicAverageShares': '',
            'TaxEffectOfUnusualItems': '',
            'GainOnSaleOfSecurity': '',
            'NormalizedIncome': '',
            'NetIncomeContinuousOperations': '',
            'OperatingExpense': '',
            'OtherSpecialCharges': '',
            'BasicEPS': '',
            'RestructuringAndMergernAcquisition': '',
            'DepreciationAndAmortizationInIncomeStatement': '',
            'RentExpenseSupplemental': '',
            'GainOnSaleOfBusiness': '',
            'TotalOtherFinanceCost': '',
            'NormalizedBasicEPS': '',
            'NormalizedDilutedEPS': '',
            'ReportedNormalizedBasicEPS': '',
            'DividendPerShare': '',
            'ProvisionForDoubtfulAccounts': '',
            'BasicExtraordinary': '',
            'OtherTaxes': '',
            'InsuranceAndClaims': '',
            'RentAndLandingFees': '',
            'NetIncomeFromTaxLossCarryforward': '',
            'MinorityInterests': '',
            'BasicDiscontinuousOperations': '',
            'ExciseTaxes': '',
            'DilutedDiscontinuousOperations': '',
            'DilutedExtraordinary': '',
            'DilutedContinuousOperations': '',
            'DepreciationIncomeStatement': '',
            'OtherOperatingExpenses': '',
            'Amortization': '',
            'SecuritiesAmortization': '',
            'BasicEPSOtherGainsLosses': '',
            'BasicContinuousOperations': '',
            'TaxLossCarryforwardBasicEPS': '',
            'GainOnSaleOfPPE': '',
            'ContinuingAndDiscontinuedDilutedEPS': '',
            'OtherunderPreferredStockDividend': '',
            'NetIncomeDiscontinuousOperations': '',
            'AmortizationOfIntangiblesIncomeStatement': '',
            'DepletionIncomeStatement': '',
            'TaxLossCarryforwardDilutedEPS': '',
            'ReportedNormalizedDilutedEPS': '',
            'DilutedAccountingChange': '',
            'DilutedEPSOtherGainsLosses': '',
            'BasicAccountingChange': '',
            'EarningsFromEquityInterestNetOfTax': '',
            'ContinuingAndDiscontinuedBasicEPS': '',
            'AverageDilutionEarnings': ''
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
            'Net Income/Starting Line': 'ONET',
            'Cash From Operating Activities': 'OTLO',
            'Depreciation/Depletion': 'SDED',
            'Amortization': 'SAMT',
            'Deferred Taxes': 'OBDT',
            'Non-Cash Items': 'SNCI',
            'Cash Receipts': '0XCR',
            'Cash Payments': '0XCP',
            'Cash Taxes Paid': 'SCTP',
            'Cash Interest Paid': 'SCIP',
            'Changes in Working Capital': 'SOCF',
            'Cash From Investing Activities': 'ITLI',
            'Capital Expenditures': 'SCEX',
            'Other Investing Cash Flow Items, Total': 'SICF',
            'Cash From Financing Activities': 'FTLF',
            'Financing Cash Flow Items': 'SFCF',
            'Total Cash Dividends Paid': 'FCDP',
            'Issuance (Retirement) of Stock, Net': 'FPSS',
            'Issuance (Retirement) of Debt, Net': 'FPRD',
            'Foreign Exchange Effects': 'SFEE',
            'Net Change in Cash': 'SNCC',
            'Beginning Cash Balance': '0BCB',
            'Ending Cash Balance': '0ECB',
            'Free Cash Flow': '0FCFE',
            'Free Cash Flow Growth': '0FCFG',
            'Free Cash Flow Yield': '0FCFY'
        },
    'BAL':
        {
            'Total Current Assets': 'ATCA',
            'Cash & Due from Banks': 'ACDB',
            'Other Earning Assets, Total': 'SOEA',
            'Net Loans': 'ANTL',
            'Cash and Short Term Investments': 'SCSI',
            'Cash': 'ACSH',
            'Total Deposits': 'LDBT',
            'Cash & Equivalents': 'ACAE',
            'Short Term Investments': 'ASTI',
            'Total Receivables, Net': 'ATRC',
            'Accounts Receivables - Trade, Net': 'AACR',
            'Total Inventory': 'AITL',
            'Prepaid Expenses': 'APPY',
            'Other Current Assets, Total': 'SOCA',
            'Total Assets': 'ATOT',
            'Property/Plant/Equipment, Total - Net': 'APPN',
            'Property/Plant/Equipment, Total - Gross': 'APTC',
            'Accumulated Depreciation, Total': 'ADEP',
            'Goodwill, Net': 'AGWI',
            'Intangibles, Net': 'AINT',
            'Long Term Investments': 'SINV',
            'Note Receivable - Long Term': 'ALTR',
            'Other Long Term Assets, Total': 'SOLA',
            'Other Assets, Total': 'SOAT',
            'Total Current Liabilities': 'LTCL',
            'Other Bearing Liabilities, Total': 'SOBL',
            'Accounts Payable': 'LAPB',
            'Payable/Accrued': 'LPBA',
            'Accrued Expenses': 'LAEX',
            'Notes Payable/Short Term Debt': 'LSTD',
            'Current Port. of LT Debt/Capital Leases': 'LCLD',
            'Other Current liabilities, Total': 'SOCL',
            'Total Liabilities': 'LTLL',
            'Total Short Term Borrowings': 'LSTB',
            'Total Long Term Debt': 'LTTD',
            'Long Term Debt': 'LLTD',
            'Capital Lease Obligations': 'LCLO',
            'Deferred Income Tax': 'SBDT',
            'Minority Interest': 'LMIN',
            'Other Liabilities, Total': 'SLTL',
            'Total Equity': 'QTLE',
            'Redeemable Preferred Stock, Total': 'SRPR',
            'Preferred Stock - Non Redeemable, Net': 'SPRS',
            'Common Stock, Total': 'SCMS',
            'Additional Paid-In Capital': 'QPIC',
            'Retained Earnings (Accumulated Deficit)': 'QRED',
            'Treasury Stock - Common': 'QTSC',
            'ESOP Debt Guarantee': 'QEDG',
            'Unrealized Gain (Loss)': 'QUGL',
            'Other Equity, Total': 'SOTE',
            "Total Liabilities & Shareholders' Equity": 'QTEL',
            'Total Common Shares Outstanding': 'QTCO',
            'Total Preferred Shares Outstanding': 'QTPO'
        },
    'INC':
        {
            'Net Interest Income': 'ENII',
            'Interest Income, Bank': 'SIIB',
            'Total Interest Expense': 'STIE',
            'Loan Loss Provision': 'ELLP',
            'Net Interest Income After Loan Loss Provision': 'SIAP',
            'Non-Interest Income, Bank': 'SNII',
            'Non-Interest Expense, Bank': 'SNIE',
            'Total Revenue': 'RTLR',
            'Revenue': 'SREV',
            'Other Revenue, Total': 'SORE',
            'Cost of Revenue, Total': 'SCOR',
            'Gross Profit': 'SGRP',
            'Total Operating Expenses': 'ETOE',
            'Selling/General/Admin. Expenses, Total': 'SSGA',
            'Research & Development': 'ERAD',
            'Depreciation / Amortization': 'SDPR',
            'Interest Expense (Income) - Net Operating': 'SINN',
            'Unusual Expense (Income)': 'SUIE',
            'Other Operating Expenses, Total': 'SOOE',
            'Operating Income': 'SOPI',
            'Interest Income (Expense), Net Non-Operating': 'SNIN',
            'Gain (Loss) on Sale of Assets': 'NGLA',
            'Other, Net': 'SONT',
            'Net Income Before Taxes': 'EIBT',
            'Provision for Income Taxes': 'TTAX',
            'Net Income After Taxes': 'TIAT',
            'Minority Interest': 'CMIN',
            'Equity In Affiliates': 'CEIA',
            'U.S GAAP Adjustment': 'CGAP',
            'Net Income Before Extraordinary Items': 'NIBX',
            'Total Extraordinary Items': 'STXI',
            'Net Income': 'NINC',
            'Total Adjustments to Net Income': 'SANI',
            'Income Available to Common Excluding Extraordinary Items': 'CIAC',
            'Dilution Adjustment': 'SDAJ',
            'Diluted Net Income': 'SDNI',
            'Diluted Weighted Average Shares': 'SDWS',
            'Diluted EPS Excluding Extraordinary Items': 'SDBF',  # divide
            'DPS - Common Stock Primary Issue': 'DDPS1',  # divide
            'Diluted Normalized EPS': 'VDES'  # divide
        }
}

#
# Interactive Brokers
#

IBFundamentalsConf = ['ticker', 'freq', 'date', 'currency', 'statement', 'code', 'value']

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
