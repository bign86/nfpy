#
# Constants
#


# Daily periods in larger time frames
DAYS_IN_1W = 7
DAYS_IN_1M = 30
DAYS_IN_1Y = 365
DAYS = {'d': 1, 'w': DAYS_IN_1W, 'm': DAYS_IN_1M, 'y': DAYS_IN_1Y}

# Business daily periods in larger time frames
BDAYS_IN_1W = 5
BDAYS_IN_1M = 21
BDAYS_IN_1Y = 252
BDAYS = {'d': 1, 'w': BDAYS_IN_1W, 'm': BDAYS_IN_1M, 'y': BDAYS_IN_1Y}

# Weekly periods in larger time frames
WEEKS_IN_1M = 4
WEEKS_IN_1Y = 52
WEEKS = {'w': 1, 'm': WEEKS_IN_1M, 'y': WEEKS_IN_1Y}

# Monthly periods in larger time frames
MONTHS_IN_1Y = 12
MONTHS = {'m': 1, 'y': MONTHS_IN_1Y}

# Numerical limits
IS_ZERO_THRS = 1e-8

# Counting day conventions
DAY_COUNT = {
    'ACT/ACT': (None, None),
    'ACT/360': (None, 360),
    'ACT/365': (None, 365),
    '30/360': (30, 360)
}

KNOWN_COUNTRIES = ['CH', 'CN', 'DE', 'EU', 'FR', 'GB', 'IT', 'JP', 'US']
