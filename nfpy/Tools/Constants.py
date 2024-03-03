#
# Constants
#


# Daily periods in larger time frames
DAYS_IN_1W = 7
DAYS_IN_1M = 30
DAYS_IN_1Q = 90
DAYS_IN_1Y = 365
DAYS = {'D': 1, 'W': DAYS_IN_1W, 'M': DAYS_IN_1M, 'Q': DAYS_IN_1Q, 'Y': DAYS_IN_1Y}

# Business daily periods in larger time frames
BDAYS_IN_1W = 5
BDAYS_IN_1M = 21
BDAYS_IN_1Q = 63
BDAYS_IN_1Y = 252
BDAYS = {'D': 1, 'B': 1, 'W': BDAYS_IN_1W, 'M': BDAYS_IN_1M, 'Q': BDAYS_IN_1Q, 'Y': BDAYS_IN_1Y}

# Weekly periods in larger time frames
WEEKS_IN_1M = 4
WEEKS_IN_1Q = 12
WEEKS_IN_1Y = 52
WEEKS = {'W': 1, 'M': WEEKS_IN_1M, 'Q': WEEKS_IN_1Q, 'Y': WEEKS_IN_1Y}

# Monthly periods in larger time frames
MONTHS_IN_1Q = 3
MONTHS_IN_1Y = 12
MONTHS = {'M': 1, 'Q': MONTHS_IN_1Q, 'Y': MONTHS_IN_1Y}

# Quarterly periods in larger time frames
QUARTERS_IN_1Y = 4
QUARTERS = {'Y': QUARTERS_IN_1Y}

# Frequency to dict
FREQ_2_D = {
    'D': DAYS,
    'B': BDAYS,
    'W': WEEKS,
    'M': MONTHS,
    'Q': QUARTERS,
}

# Numerical limits
IS_ZERO_THRS = 1e-8

# Counting day conventions
DAY_COUNT = {
    'ACT/ACT': (None, None),
    'ACT/360': (None, 360),
    'ACT/365': (None, 365),
    '30/360': (30, 360)
}

KNOWN_COUNTRIES = ['CA', 'CH', 'CN', 'DE', 'EU', 'FR', 'GB', 'IT', 'JP', 'NL', 'US']
