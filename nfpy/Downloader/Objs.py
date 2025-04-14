#
# Utility objects for the Downloader module
#

from collections import namedtuple


# Namedtuples holding the data for downloads and imports
NTDownload = namedtuple(
    'NTDownload',
    'provider, page, ticker, currency, active, update_frequency, last_update, description',
)

NTImport = namedtuple('NTImport', 'uid, ticker, provider, item, active')

# Limits for the downloaders: max number of downloads and wait time
Limits = namedtuple('Limits', ['max_num', 'wait_time'])
