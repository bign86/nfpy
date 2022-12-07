CREATE TABLE [Alerts] (
    [uid] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [cond] TEXT NOT NULL,
    [value] REAL NOT NULL,
    [triggered] BOOL,
    [date_triggered] DATETIME,
    [date_checked] DATETIME,
    PRIMARY KEY ([uid], [date], [cond], [value])
) WITHOUT ROWID;

CREATE TABLE [Bond] (
    [uid] TEXT NOT NULL,
    [isin] TEXT,
    [issuer] TEXT,
    [currency] TEXT,
    [country] TEXT,
    [description] TEXT,
    [asset_class] TEXT,
    [inception_date] DATE,
    [maturity] DATE,
    [rate_type] TEXT,
    [coupon] REAL,
    [c_per_year] INTEGER,
    [day_count] INTEGER,
    [callable] BOOL,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [BondTS] (
    [uid] TEXT NOT NULL,
    [dtype] INTEGER,
    [date] DATETIME,
    [value] REAL,
    PRIMARY KEY ([uid], [dtype], [date])
) WITHOUT ROWID;

CREATE TABLE [BorsaItalianaDividends] (
    [ticker] TEXT NOT NULL,
    [type] TEXT NOT NULL,
    [dps_bod] REAL,
    [dps_agm] REAL,
    [currency] TEXT,
    [ex_date] DATE NOT NULL,
    [payment] DATE,
    [agm] DATE,
    [notice] INTEGER,
    PRIMARY KEY ([ticker], [type], [ex_date])
) WITHOUT ROWID;

CREATE TABLE [Company] (
    [uid] TEXT NOT NULL,
    [description] TEXT,
    [name] TEXT NOT NULL,
    [sector] TEXT,
    [industry] TEXT,
    [equity] TEXT,
    [currency] TEXT,
    [country] TEXT,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [CompanyFundamentals] (
    [uid] TEXT NOT NULL,
    [code] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [freq] TEXT NOT NULL,
    [value] REAL,
    PRIMARY KEY ([uid], [code], [date], [freq]),
    foreign key ([uid]) references Company([uid])
) WITHOUT ROWID;

CREATE TABLE [Currency] (
    [name] TEXT,
    [symbol] TEXT NOT NULL,
    [country] TEXT,
    [pegged] TEXT,
    [factor] REAL,
    PRIMARY KEY ([symbol])
) WITHOUT ROWID;

CREATE TABLE [Curve] (
    [uid] TEXT NOT NULL,
    [description] TEXT,
    [currency] TEXT,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [CurveConstituents] (
    [uid] TEXT NOT NULL,
    [bucket] TEXT NOT NULL,
    PRIMARY KEY ([uid], [bucket])
) WITHOUT ROWID;

CREATE TABLE [DecDatatype] (
    [datatype] TEXT NOT NULL,
    [encoding] INTEGER,
    PRIMARY KEY ([datatype])
) WITHOUT ROWID;

CREATE TABLE [Downloads] (
    [provider] TEXT NOT NULL,
    [page] TEXT NOT NULL,
    [ticker] TEXT NOT NULL,
    [currency] TEXT,
    [active] BOOL NOT NULL,
    [update_frequency] INTEGER NOT NULL,
    [last_update] DATE,
    [description] TEXT,
    PRIMARY KEY ([provider], [page], [ticker])
) WITHOUT ROWID;

CREATE TABLE [ECBSeries] (
    [ticker] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [value] REAL,
    PRIMARY KEY ([ticker], [date])
) WITHOUT ROWID;

CREATE TABLE [Equity] (
    [uid] TEXT NOT NULL,
    [ticker] TEXT NOT NULL,
    [isin] TEXT NOT NULL,
    [description] TEXT,
    [country] TEXT,
    [market] TEXT,
    [currency] TEXT NOT NULL,
    [company] TEXT,
    [preferred] BOOL,
    [index] TEXT,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [EquityTS] (
    [uid] TEXT NOT NULL,
    [dtype] INTEGER NOT NULL,
    [date] DATETIME NOT NULL,
    [value] REAL,
    PRIMARY KEY ([uid], [dtype], [date])
) WITHOUT ROWID;

CREATE TABLE [Etf] (
    [uid] TEXT NOT NULL,
    [ticker] TEXT NOT NULL,
    [isin] TEXT NOT NULL,
    [description] TEXT,
    [country] TEXT,
    [ac] TEXT,
    [currency] TEXT NOT NULL,
    [index] TEXT,
    [issuer] TEXT,
    [fees] REAL NOT NULL,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [EtfTS] (
    [uid] TEXT NOT NULL,
    [dtype] INTEGER NOT NULL,
    [date] DATETIME NOT NULL,
    [value] REAL,
    PRIMARY KEY ([uid], [dtype], [date])
) WITHOUT ROWID;

CREATE TABLE [Fx] (
    [uid] TEXT NOT NULL,
    [description] TEXT,
    [price_country] TEXT,
    [base_country] TEXT,
    [price_ccy] TEXT,
    [base_ccy] TEXT,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [FxTS] (
    [uid] TEXT NOT NULL,
    [dtype] INTEGER NOT NULL,
    [date] DATETIME NOT NULL,
    [value] REAL,
    PRIMARY KEY ([uid], [dtype], [date])
) WITHOUT ROWID;

CREATE TABLE [IBFinancials] (
    [ticker] TEXT,
    [freq] TEXT,
    [date] DATE,
    [currency] TEXT,
    [statement] TEXT,
    [code] TEXT,
    [value] REAL,
    PRIMARY KEY ([ticker], [freq], [date], [statement], [code])
) WITHOUT ROWID;

CREATE TABLE [Imports] (
    [uid] TEXT NOT NULL,
    [ticker] TEXT NOT NULL,
    [provider] TEXT NOT NULL,
    [item] TEXT NOT NULL,
    [active] BOOL NOT NULL,
    PRIMARY KEY ([uid], [ticker], [provider], [item])
) WITHOUT ROWID;

CREATE TABLE [Indices] (
    [uid] TEXT NOT NULL,
    [ticker] TEXT NOT NULL,
    [area] TEXT,
    [currency] TEXT NOT NULL,
    [description] TEXT,
    [ac] TEXT,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [IndexTS] (
    [uid] TEXT NOT NULL,
    [dtype] INTEGER NOT NULL,
    [date] DATE NOT NULL,
    [value] REAL,
    PRIMARY KEY ([uid], [dtype], [date]),
    foreign key ([uid]) references Indices([uid])
) WITHOUT ROWID;

CREATE TABLE [InvestingEvents] (
    [ticker] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [dtype] TEXT NOT NULL,
    [value] REAL,
    PRIMARY KEY ([ticker], [date], [dtype])
) WITHOUT ROWID;

CREATE TABLE [InvestingFinancials] (
    [ticker] TEXT NOT NULL,
    [freq] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [currency] TEXT,
    [statement] TEXT NOT NULL,
    [code] TEXT NOT NULL,
    [value] REAL,
    PRIMARY KEY ([ticker], [freq], [date], [statement], [code])
) WITHOUT ROWID;

CREATE TABLE [InvestingPrices] (
    [ticker] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [price] REAL,
    [open] REAL,
    [high] REAL,
    [low] REAL,
    [volume] INTEGER,
    PRIMARY KEY ([ticker], [date])
) WITHOUT ROWID;

CREATE TABLE [ManualPrices] (
    [ticker] TEXT NOT NULL,
    [date] DATETIME NOT NULL,
    [open] REAL,
    [close] REAL,
    [adj_close] REAL,
    [volume] INTEGER,
    PRIMARY KEY ([ticker], [date])
) WITHOUT ROWID;

CREATE TABLE [MapFinancials] (
    [short_name] TEXT NOT NULL,
    [category] TEXT,
    [long_name] TEXT,
    PRIMARY KEY ([short_name])
) WITHOUT ROWID;

CREATE TABLE [NasdaqDividends] (
    [ticker] TEXT NOT NULL,
	[type] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [amount] REAL,
    [declaration_date] DATE,
    [record_date] DATE,
    [payment_date] DATE,
    PRIMARY KEY ([ticker], [type], [date])
) WITHOUT ROWID;

CREATE TABLE [NasdaqPrices] (
    [ticker] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [close] REAL,
    [open] REAL,
    [high] REAL,
    [low] REAL,
    [volume] INTEGER,
    PRIMARY KEY ([ticker], [date])
) WITHOUT ROWID;

CREATE TABLE [OECDSeries] (
    [ticker] TEXT NOT NULL,
    [location] TEXT NOT NULL,
    [country] TEXT,
    [transact_code] TEXT NOT NULL,
    [transact] TEXT,
    [measure_code] TEXT NOT NULL,
    [measure] TEXT,
    [frequency_code] TEXT NOT NULL,
    [frequency] TEXT NOT NULL,
    [date_code] SHORTDATE NOT NULL,
    [date] TEXT,
    [unit_code] TEXT,
    [unit] TEXT,
    [powercode_code] INTEGER,
    [powercode] TEXT,
    [value] REAL NOT NULL,
    PRIMARY KEY ([location], [transact_code], [measure_code], [frequency], [date_code])
) WITHOUT ROWID;

CREATE TABLE [Portfolio] (
    [uid] TEXT NOT NULL,
    [name] TEXT,
    [description] TEXT,
    [currency] TEXT,
    [inception_date] DATE,
    [benchmark] TEXT,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [PortfolioPositions] (
    [ptf_uid] TEXT NOT NULL,
    [date] DATETIME NOT NULL,
    [pos_uid] TEXT NOT NULL,
    [type] TEXT NOT NULL,
    [currency] TEXT NOT NULL,
    [quantity] REAL NOT NULL,
    [alp] REAL NOT NULL,
    PRIMARY KEY ([ptf_uid], [date], [pos_uid])
) WITHOUT ROWID;

CREATE TABLE [Providers] (
    [provider] TEXT NOT NULL,
    [page] TEXT NOT NULL,
    [item] TEXT NOT NULL,
    PRIMARY KEY ([provider], [page], [item])
) WITHOUT ROWID;

CREATE TABLE [Rate] (
    [uid] TEXT NOT NULL,
    [description] TEXT,
    [currency] TEXT,
    [country] BOOL NOT NULL,
    [tenor] REAL,
    [frequency] TEXT NOT NULL,
    [is_ccy_rf] BOOL NOT NULL DEFAULT False,
    [is_country_rf] BOOL NOT NULL DEFAULT False,
    [is_inflation] BOOL NOT NULL DEFAULT False,
    [is_gdp] BOOL NOT NULL DEFAULT False,
    PRIMARY KEY ([uid])
) WITHOUT ROWID;

CREATE TABLE [RateTS] (
    [uid] TEXT NOT NULL,
    [dtype] INTEGER NOT NULL,
    [date] DATE NOT NULL,
    [value] REAL,
    PRIMARY KEY ([uid], [dtype], [date])
) WITHOUT ROWID;

CREATE TABLE [Reports] (
    [id] TEXT NOT NULL,
    [title] TEXT,
    [description] TEXT,
    [report] TEXT,
    [template] TEXT,
    [uids] PARAMETERS,
    [parameters] PARAMETERS,
    [active] BOOL,
    PRIMARY KEY ([id])
) WITHOUT ROWID;

CREATE TABLE [SystemInfo] (
    [field] TEXT NOT NULL,
    [value] REAL,
    [date] DATE,
    PRIMARY KEY ([field])
) WITHOUT ROWID;

CREATE TABLE [Trades] (
    [ptf_uid] TEXT NOT NULL,
    [date] DATETIME NOT NULL,
    [pos_uid] TEXT NOT NULL,
    [buy_sell] BOOL NOT NULL,
    [currency] TEXT NOT NULL,
    [quantity] REAL NOT NULL,
    [price] REAL NOT NULL,
    [costs] REAL,
    [market] TEXT,
    PRIMARY KEY ([ptf_uid], [date], [pos_uid]),
    foreign key ([ptf_uid]) references Portfolio([uid])
) WITHOUT ROWID;

CREATE TABLE [YahooDividends] (
    [ticker] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [value] REAL,
    PRIMARY KEY ([ticker], [date])
) WITHOUT ROWID;

CREATE TABLE [YahooSplits] (
    [ticker] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [value] TEXT,
    PRIMARY KEY ([ticker], [date])
) WITHOUT ROWID;

CREATE TABLE [YahooFinancials] (
    [ticker] TEXT NOT NULL,
    [freq] TEXT NOT NULL,
    [currency] TEXT,
    [statement] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [code] TEXT NOT NULL,
    [value] REAL,
    PRIMARY KEY ([ticker], [freq], [date], [statement], [code])
) WITHOUT ROWID;

CREATE TABLE [YahooPrices] (
    [ticker] TEXT NOT NULL,
    [date] DATE NOT NULL,
    [open] REAL,
    [high] REAL,
    [low] REAL,
    [close] REAL,
    [adj_close] REAL,
    [volume] INTEGER,
    PRIMARY KEY ([ticker], [date])
) WITHOUT ROWID;

CREATE VIEW [Assets] AS
SELECT [uid], [type], [description], [currency]
FROM (
    SELECT [uid], 'Bond'      as [type], [description], [currency] FROM [Bond] UNION
    SELECT [uid], 'Company'   as [type], [description], [currency] FROM [Company] UNION
    SELECT [uid], 'Curve'     as [type], [description], [currency] FROM [Curve] UNION
    SELECT [uid], 'Equity'    as [type], [description], [currency] FROM [Equity] UNION
    SELECT [uid], 'Etf'       as [type], [description], [currency] FROM [Etf] UNION
    SELECT [uid], 'Fx'        as [type], [description], NULL FROM [Fx] UNION
    SELECT [uid], 'Indices'   as [type], [description], [currency] FROM [Indices] UNION
    SELECT [uid], 'Portfolio' as [type], [description], NULL FROM [Portfolio] UNION
    SELECT [uid], 'Rate'      as [type], [description], NULL FROM [Rate]
) AS src;

