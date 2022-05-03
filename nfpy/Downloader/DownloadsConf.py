#
# Configurations for Downloads
#


#
# Yahoo
#

# YahooFinancialsConf = [
#     ['date', 'freq'],
#     # ['earningsActual', 'earningsEstimate'],
#     [  # IncomeStatement
#         'researchDevelopment', 'effectOfAccountingCharges',
#         'incomeBeforeTax', 'minorityInterest', 'netIncome', 'sellingGeneralAdministrative',
#         'grossProfit', 'ebit', 'operatingIncome', 'otherOperatingExpenses', 'interestExpense',
#         'extraordinaryItems', 'nonRecurring', 'otherItems', 'incomeTaxExpense',
#         'totalRevenue', 'totalOperatingExpenses', 'costOfRevenue', 'totalOtherIncomeExpenseNet',
#         'discontinuedOperations', 'netIncomeFromContinuingOps', 'netIncomeApplicableToCommonShares'
#     ],
#     [  # BalanceSheet
#         'intangibleAssets', 'totalLiab', 'totalStockholderEquity',
#         'deferredLongTermLiab', 'otherCurrentLiab', 'totalAssets', 'commonStock',
#         'otherCurrentAssets', 'retainedEarnings', 'otherLiab', 'goodWill', 'treasuryStock',
#         'otherAssets', 'cash', 'totalCurrentLiabilities', 'deferredLongTermAssetCharges',
#         'shortLongTermDebt', 'otherStockholderEquity', 'propertyPlantEquipment',
#         'totalCurrentAssets', 'longTermInvestments', 'netTangibleAssets', 'shortTermInvestments',
#         'netReceivables', 'longTermDebt', 'inventory', 'accountsPayable', 'capitalSurplus'
#     ],
#     [  # CashFlow
#         # NOTE: netIncome is renamed CFnetIncome to avoid clashing with Income statement
#         'changeToLiabilities', 'totalCashflowsFromInvestingActivities', 'repurchaseOfStock',
#         'netBorrowings', 'totalCashFromFinancingActivities', 'changeToOperatingActivities',
#         'netIncome', 'changeInCash', 'effectOfExchangeRate', 'totalCashFromOperatingActivities',
#         'depreciation', 'otherCashflowsFromInvestingActivities', 'dividendsPaid',
#         'changeToInventory', 'changeToAccountReceivables', 'otherCashflowsFromFinancingActivities',
#         'changeToNetincome', 'capitalExpenditures', 'investments', 'issuanceOfStock'
#     ]
# ]

YahooFinancialsConf = {
    'INC':
        {
            'researchDevelopment': '',
            'effectOfAccountingCharges': '',
            'incomeBeforeTax': '',
            'minorityInterest': '',
            'netIncome': '',
            'sellingGeneralAdministrative': '',
            'grossProfit': '',
            'ebit': '',
            'operatingIncome': '',
            'otherOperatingExpenses': '',
            'interestExpense': '',
            'extraordinaryItems': '',
            'nonRecurring': '',
            'otherItems': '',
            'incomeTaxExpense': '',
            'totalRevenue': '',
            'totalOperatingExpenses': '',
            'costOfRevenue': '',
            'totalOtherIncomeExpenseNet': '',
            'discontinuedOperations': '',
            'netIncomeFromContinuingOps': '',
            'netIncomeApplicableToCommonShares': ''
        },
    'BAL':
        {
            'intangibleAssets': '',
            'totalLiab': '',
            'totalStockholderEquity': '',
            'deferredLongTermLiab': '',
            'otherCurrentLiab': '',
            'totalAssets': '',
            'commonStock': '',
            'otherCurrentAssets': '',
            'retainedEarnings': '',
            'otherLiab': '',
            'goodWill': '',
            'treasuryStock': '',
            'otherAssets': '',
            'cash': '',
            'totalCurrentLiabilities': '',
            'deferredLongTermAssetCharges': '',
            'shortLongTermDebt': '',
            'otherStockholderEquity': '',
            'propertyPlantEquipment': '',
            'totalCurrentAssets': '',
            'longTermInvestments': '',
            'netTangibleAssets': '',
            'shortTermInvestments': '',
            'netReceivables': '',
            'longTermDebt': '',
            'inventory': '',
            'accountsPayable': '',
            'capitalSurplus': ''
        },
    'CAS':
        {
            # NOTE: netIncome is renamed CFnetIncome to avoid clashing with Income statement
            'changeToLiabilities': '',
            'totalCashflowsFromInvestingActivities': '',
            'repurchaseOfStock': '',
            'netBorrowings': '',
            'totalCashFromFinancingActivities': '',
            'changeToOperatingActivities': '',
            'netIncome': '',
            'changeInCash': '',
            'effectOfExchangeRate': '',
            'totalCashFromOperatingActivities': '',
            'depreciation': '',
            'otherCashflowsFromInvestingActivities': '',
            'dividendsPaid': '',
            'changeToInventory': '',
            'changeToAccountReceivables': '',
            'otherCashflowsFromFinancingActivities': '',
            'changeToNetincome': '',
            'capitalExpenditures': '',
            'investments': '',
            'issuanceOfStock': ''
        }
}

YahooHistPricesConf = ["date", "open", "high", "low", "close", "adj_close", "volume"]

YahooHistDividendsConf = ["date", "value"]

YahooHistSplitsConf = ["date", "value"]

#
# ECB
#

ECBSeriesConf = ["date", "value"]

#
# Investing
#

InvestingSeriesConf = ["date", "price", "open", "high", "low", "volume"]

InvestingCashFlowConf = {'Net Income/Starting Line': 'ONET',
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
                         }

InvestingBalanceSheetConf = {'Total Current Assets': 'ATCA',
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
                             }

InvestingIncomeStatementConf = {'Net Interest Income': 'ENII',
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

#
# Interactive Brokers
#

IBFundamentalsConf = ['ticker', 'freq', 'date', 'currency', 'statement', 'code', 'value']
