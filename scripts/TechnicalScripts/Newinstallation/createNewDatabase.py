#
# Create Database script
# Creates a new database from scratch
#

import json
import os
import pickle
from pathlib import Path

from nfpy import NFPY_ROOT_DIR
from nfpy.Configuration import get_conf_glob
import nfpy.DB as DB

__version__ = '0.2'
_TITLE_ = "<<< Database creation script >>>"

Q_DEC = "insert into DecDatatype (datatype, encoding) values (?, ?);"
Q_SYS = "insert into SystemInfo (field, value) values (?, ?);"
Q_FMAP = "insert into MapFinancials (short_name, category, long_name) values (?, ?, ?);"

PKL_FILE = 'db_static_data.p'
JSN_FILE = 'db_static_data.json'

TABLES_TO_CREATE = [
    (
        'Bond',
        """create table Bond (uid TEXT, isin TEXT NOT NULL, issuer TEXT NOT NULL,
            currency TEXT NOT NULL, description TEXT, asset_class TEXT,
            inception_date DATETIME, maturity DATETIME NOT NULL, rate_type TEXT NOT NULL,
            coupon REAL, c_per_year INTEGER, day_count INTEGER, callable BOOL NOT NULL,
            primary key (uid)) without rowid;"""
    ),
    (
        'BondTS',
        """create table BondTS (uid TEXT, dtype INTEGER NOT NULL, date DATETIME NOT NULL,
            value REAL NOT NULL, primary key (uid,dtype,date), foreign key (uid)
            references Bond(uid)) without rowid;"""
    ),
    (
        'Company',
        """create table Company (uid TEXT, description TEXT, name TEXT NOT NULL,
            sector TEXT, industry TEXT, currency TEXT, country TEXT,
            primary key (uid)) without rowid;"""
    ),
    (
        'CompanyFundamentals',
        """create table CompanyFundamentals (uid TEXT, code TEXT,
        date DATETIME, freq TEXT, value REAL, primary key (uid, code, date, freq),
        foreign key (uid) references Company(uid)) without rowid;"""
    ),
    (
        'Currency',
        """create table Currency (uid TEXT, description TEXT, base_country TEXT,
            tgt_country TEXT, base_fx TEXT NOT NULL, tgt_ccy TEXT NOT NULL,
            primary key (uid)) without rowid;"""
    ),
    (
        'CurrencyTS',
        """create table CurrencyTS (uid TEXT, dtype INTEGER NOT NULL,
            date DATETIME NOT NULL, value REAL NOT NULL,
            primary key (uid,dtype,date), foreign key (uid)
            references Currency(uid)) without rowid;"""
    ),
    (
        'Curve',
        """create table Curve (uid TEXT, description TEXT, currency TEXT,
            primary key (uid)) without rowid;"""
    ),
    (
        'CurveConstituents',
        """create table CurveConstituents (uid TEXT, bucket TEXT NOT NULL,
            primary key (uid, bucket), foreign key (uid) references Rate(uid),
            foreign key (bucket) references Curve(uid)) without rowid;"""
    ),
    (
        'DecDatatype',
        """create table DecDatatype (datatype TEXT, encoding INTEGER NOT NULL,
            primary key (datatype)) without rowid;"""
    ),
    (
        'Downloads',
        """create table Downloads (uid TEXT, provider TEXT, page TEXT, ticker TEXT NOT NULL,
            currency TEXT, active BOOL NOT NULL,
            update_frequency INTEGER NOT NULL, last_update DATETIME,
            primary key (provider, page, ticker)) without rowid;"""
    ),
    (
        'ECBSeries',
        """create table ECBSeries (ticker TEXT, date DATETIME, value REAL,
            primary key (ticker, date)) without rowid;"""
    ),
    (
        'Equity',
        """create table Equity (uid TEXT, isin TEXT NOT NULL, description TEXT,
            country TEXT, currency TEXT NOT NULL, company_uid TEXT,
            preferred BOOL, [index] TEXT, primary key (uid),
            foreign key (company_uid) references Company(uid)) without rowid;"""
    ),
    (
        'EquityTS',
        """create table EquityTS (uid TEXT, dtype INTEGER NOT NULL, date DATETIME NOT NULL,
            value REAL NOT NULL, primary key (uid,dtype,date), foreign key (uid)
            references Equity(uid)) without rowid;"""
    ),
    (
        'IBFinancials',
        """create table IBFinancials (ticker TEXT, freq TEXT, date DATETIME,
            currency TEXT, statement TEXT, code TEXT, value REAL,
            primary key (ticker, freq, date, statement, code)) without rowid;"""
    ),
    (
        'Imports',
        """create table Imports (uid TEXT NOT NULL, ticker TEXT, provider TEXT, page TEXT,
            src_column TEXT, tgt_datatype TEXT NOT NULL, active BOOL NOT NULL,
            primary key (ticker, provider, page, src_column)) without rowid;"""
    ),
    (
        'Indices',
        """create table Indices (uid TEXT, area TEXT, currency TEXT NOT NULL,
            description TEXT, asset_class TEXT, primary key (uid)) without rowid;"""
    ),
    (
        'IndexTS',
        """create table IndexTS (uid TEXT, dtype INTEGER NOT NULL, date DATETIME NOT NULL,
            value REAL NOT NULL, primary key (uid,dtype,date), foreign key (uid)
            references Indices(uid)) without rowid;"""
    ),
    (
        'InvestingFinancials',
        """create table InvestingFinancials (ticker TEXT, freq TEXT, date DATETIME,
            currency TEXT, statement TEXT, code TEXT, value REAL,
            primary key (ticker, freq, date, statement, code) ) without rowid;"""
    ),
    (
        'InvestingPrices',
        """create table InvestingPrices (ticker TEXT, date DATETIME, price REAL, open REAL,
            high REAL, low REAL, volume INTEGER, primary key (ticker, date)) without rowid;"""
    ),
    (
        'MapFinancials',
        """create table MapFinancials (short_name TEXT, category TEXT,
            long_name TEXT, primary key (short_name)) without rowid;"""
    ),
    (
        'Portfolio',
        """create table Portfolio (uid TEXT, name TEXT, description TEXT,
            currency TEXT NOT NULL, inception_date DATETIME NOT NULL,
            benchmark TEXT, primary key (uid)) without rowid;"""
    ),
    (
        'PortfolioPositions',
        """create table PortfolioPositions (ptf_uid TEXT, date DATETIME, pos_uid TEXT,
            asset_uid TEXT NOT NULL, type TEXT NOT NULL, currency TEXT NOT NULL,
            quantity REAL NOT NULL, alp REAL NOT NULL,
            primary key (ptf_uid, date, pos_uid), foreign key (ptf_uid)
            references Portfolio(uid)) without rowid;"""
    ),
    (
        'Rate',
        """create table Rate (uid TEXT, description TEXT, currency TEXT, tenor REAL,
            is_rf BOOL NOT NULL, primary key (uid)) without rowid;"""
    ),
    (
        'RateTS',
        """create table RateTS (uid TEXT, dtype INTEGER NOT NULL, date DATETIME NOT NULL,
            value REAL NOT NULL, primary key (uid, dtype, date), foreign key (uid)
            references Rate(uid)) without rowid;"""
    ),
    (
        'Reports',
        """create table Reports (uid TEXT, model TEXT, parameters TEXT,
            active BOOL NOT NULL, primary key (uid, model)) without rowid;"""
    ),
    (
        'SystemInfo',
        """create table SystemInfo (field TEXT, value REAL NOT NULL,
            primary key (field)) without rowid;"""
    ),
    (
        'Trades',
        """create table Trades (ptf_uid TEXT, date DATETIME, pos_uid TEXT,
            buy_sell BOOL NOT NULL, currency TEXT NOT NULL, quantity REAL NOT NULL,
            price REAL NOT NULL, costs REAL, market TEXT, primary key (ptf_uid, date, pos_uid),
            foreign key (ptf_uid) references Portfolio(uid)) without rowid;"""
    ),
    (
        'YahooEvents',
        """create table YahooEvents (ticker TEXT, date DATETIME, dtype TEXT,
            value REAL, primary key (ticker, date, dtype)) without rowid;"""
    ),
    (
        'YahooFinancials',
        """create table YahooFinancials (ticker TEXT, date DATETIME, freq TEXT,
           researchDevelopment INTEGER, effectOfAccountingCharges INTEGER, incomeBeforeTax INTEGER,
           minorityInterest INTEGER, netIncome INTEGER, sellingGeneralAdministrative INTEGER,
           grossProfit INTEGER, ebit INTEGER, operatingIncome INTEGER,
           otherOperatingExpenses INTEGER, interestExpense INTEGER, extraordinaryItems INTEGER,
           nonRecurring INTEGER, otherItems INTEGER, incomeTaxExpense INTEGER, totalRevenue INTEGER,
           totalOperatingExpenses INTEGER, costOfRevenue INTEGER,
           totalOtherIncomeExpenseNet INTEGER, discontinuedOperations INTEGER,
           netIncomeFromContinuingOps INTEGER, netIncomeApplicableToCommonShares INTEGER,
           intangibleAssets INTEGER, totalLiab INTEGER, totalStockholderEquity INTEGER,
           deferredLongTermLiab INTEGER, otherCurrentLiab INTEGER, totalAssets INTEGER,
           commonStock INTEGER, otherCurrentAssets INTEGER, retainedEarnings INTEGER,
           otherLiab INTEGER, goodWill INTEGER, treasuryStock INTEGER, otherAssets INTEGER,
           cash INTEGER, totalCurrentLiabilities INTEGER, deferredLongTermAssetCharges INTEGER,
           shortLongTermDebt INTEGER, otherStockholderEquity INTEGER,
           propertyPlantEquipment INTEGER, totalCurrentAssets INTEGER, longTermInvestments INTEGER,
           netTangibleAssets INTEGER, shortTermInvestments INTEGER, netReceivables INTEGER,
           longTermDebt INTEGER, inventory INTEGER, accountsPayable INTEGER, capitalSurplus INTEGER,
           changeToLiabilities INTEGER, totalCashflowsFromInvestingActivities INTEGER,
           repurchaseOfStock INTEGER, netBorrowings INTEGER,
           totalCashFromFinancingActivities INTEGER, changeToOperatingActivities INTEGER,
           CFnetIncome INTEGER, changeInCash INTEGER, effectOfExchangeRate INTEGER,
           totalCashFromOperatingActivities INTEGER, depreciation INTEGER,
           otherCashflowsFromInvestingActivities INTEGER, dividendsPaid INTEGER,
           changeToInventory INTEGER, changeToAccountReceivables INTEGER,
           otherCashflowsFromFinancingActivities INTEGER, changeToNetincome INTEGER,
           capitalExpenditures INTEGER, investments INTEGER, issuanceOfStock INTEGER,
           primary key (ticker, date, freq)) without rowid;"""
    ),
    (
        'YahooPrices',
        """create table YahooPrices (ticker TEXT, date DATETIME, open REAL,
            high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER,
            primary key (ticker, date)) without rowid;"""
    ),
]

VIEWS_TO_CREATE = [
    (
        'Assets',
        """CREATE VIEW Assets AS SELECT uid, type, description FROM
            (
                SELECT uid, 'Equity' as type, description FROM Equity union
                SELECT uid, 'Bond' as type, description FROM Bond union
                SELECT uid, 'Rate' as type, description FROM Rate union
                SELECT uid, 'Curve' as type, description FROM Curve union
                SELECT uid, 'Currency' as type, description FROM Currency union
                SELECT uid, 'Indices' as type, description FROM Indices union
                SELECT uid, 'Portfolio' as type, description FROM Portfolio union
                SELECT uid, 'Company' as type, description FROM Company
            ) AS src;"""
    ),
]


def get_db_handler():
    db_path = get_conf_glob().db_dir
    if not os.path.isfile(db_path):
        raise ValueError('Cannot create database.')

    # database creation
    print('Creating the new database...')
    db_ = DB.get_db_glob()

    if not db_:
        raise RuntimeError('I can not connect to the database... Sorry, but I got to stop here :(')
    print("New database created in {}".format(db_.db_path))

    return db_


def create_database(db_):
    # create tables
    print('Creating tables...')
    for t, q in TABLES_TO_CREATE:
        print("Create table {}... ".format(t), end="")
        db_.execute(q)
        print("done!")

    print("--- Tables created! ---")

    # create views
    print('Creating views...')
    for t, q in VIEWS_TO_CREATE:
        print("Create view {}... ".format(t), end="")
        db_.execute(q)
        print("done!")

    print("--- Views created! ---")


def populate_database(db_):
    """ Populate database """

    try:
        data_file = Path(os.path.join(NFPY_ROOT_DIR, PKL_FILE))
        data_dict = pickle.load(data_file.open('rb'))
    except Exception as ex1:
        try:
            data_file = Path(os.path.join(NFPY_ROOT_DIR, JSN_FILE))
            data_dict = json.load(data_file.open('rb'))
        except Exception as ex2:
            raise ex2

    data_file.close()

    print("Adding initial data")
    db_.executemany(Q_SYS, data_dict['DATA_SYS'])
    db_.executemany(Q_FMAP, data_dict['DATA_FINMAP'])
    db_.executemany(Q_DEC, data_dict['DATA_DEC'], commit=True)
    print("--- Setup completed! ---")


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_handler()
    create_database(db)
    populate_database(db)
