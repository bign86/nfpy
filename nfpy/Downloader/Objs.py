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
