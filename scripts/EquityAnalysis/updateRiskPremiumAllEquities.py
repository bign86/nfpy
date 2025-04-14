#
# Calculate Risk Premium
# Script to calculate the Risk Premium of an instrument on an index
# updating the DerivedSeries table in the DB
#

import argparse
import cutils
import pandas as pd
from pandas.tseries.offsets import BMonthBegin

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
from nfpy.DatatypeFactory import get_dt_glob
import nfpy.DB as DB
from nfpy.Financial.SeriesStats.RiskPremium import RiskPremium
import nfpy.IO.Utilities as Ut
from nfpy.Session import get_session
from nfpy.Tools import (Exceptions as Ex, get_logger_glob)

__version__ = '0.1'
_TITLE_ = "<<< Update risk premium series script >>>"

_TABLE_ = 'DerivedSeries'


def _fetch_last_date(_db, _series: str, _dtypes: tuple) -> Cal.TyDate | None:
    # Note that NULL is returned from MIN/MAX functions if any is present
    q = f"""
    SELECT MIN(t.date)
    FROM (
        SELECT dtype, MAX(date) AS date
        FROM {_TABLE_}
        WHERE [uid] = ? AND [dtype] IN (?,?,?,?)
    ) AS t;
    """
    res = _db.execute(q, (_series, *_dtypes)).fetchone()
    return res[0] if res else None


if __name__ == '__main__':

    # Take options
    parser = argparse.ArgumentParser()
    parser.add_argument('--horizon', nargs='?', help='calculation horizon')
    args = parser.parse_args()

    if not args.horizon:
        raise ValueError('updateBetaSeries: horizon must be given')

    # Build all factories
    af = get_af_glob()
    db = DB.get_db_glob()
    dt = get_dt_glob()
    qb = DB.get_qb_glob()
    s = get_session()

    # Initialize calendar
    s.initialize(Cal.today(mode='timestamp'), start='2000-01-01')
    cal = s.calendar
    logger = get_logger_glob()

    # Get the datatype code for beta
    RP = dt.get('RiskPremium.Historical')
    dtypes = (RP,)

    # Parse horizon
    horizon = Cal.Horizon(args.horizon)
    if not horizon.months:
        raise ValueError('updateBetaSeries: horizon must be in either months or years')

    # Take UIDs
    uids = db.execute('SELECT [uid] FROM [Index] WHERE [ac] = "Equity"').fetchall()

    # Final data
    data = []

    # Loop over UID
    for uid in uids:
        logger.info(f'<<< UID {uid[0]}')
        uid_data = []

        try:
            # Get asset
            index = af.get(uid[0])
            rf = af.get_rf(index.country)
            max_dt = None

            try:
                series = af.get_derived_series(
                    asset1=uid[0],
                    asset2=rf.uid,
                    frequency=Cal.Frequency('M'),
                    horizon=str(horizon)
                )
            except Ex.MissingData as ex:
                pass

            else:
                max_dt = _fetch_last_date(db, series.uid, dtypes)
            logger.info(f'{rf.uid} | max date {max_dt if max_dt is not None else "None"}')

            if max_dt is None:
                # Get prices
                prices = index.prices
                prices_numpy = prices.to_numpy()

                # Take the starting date of the series, and go one month forward
                # if data are incomplete for the first month.
                min_idx = cutils.next_valid_index(
                    prices_numpy,
                    0, 0,
                    prices_numpy.shape[0] - 1
                )
                min_date = prices.index[min_idx]
                cal.t0 = min_date + BMonthBegin(horizon.months + 1)
                # end_date = min_date + DateOffset(months=(horizon.months + 1))

            else:
                # max_dt = pd.Timestamp(max_dt)
                cal.t0 = pd.Timestamp(max_dt) + BMonthBegin(1)

            # If the end is past the calendar skip the calculation.
            if cal.t0 > cal.end:
                Ut.print_warn(f'{index.uid} is too late. Skipping.')
                continue

        except Ex.MissingData as ex:
            Ut.print_exc(Ex.MissingData(f'updateRiskPremiumSeries: Error in processing {uid[0]}'))
            Ut.print_exc(ex)
            continue

        logger.info(f'Starting execution at {cal.t0.strftime("%Y-%m-%d")}')

        try:
            while cal.t0 <= cal.end:
                logger.info(f't0 {cal.t0.strftime("%Y-%m-%d")}')
                rp = RiskPremium(
                    index,
                    rf,
                    Cal.Frequency.M,
                    horizon=horizon
                ).rp()

                start = pd.Timestamp(rp.start).to_pydatetime().date()
                end = pd.Timestamp(rp.end).to_pydatetime().date()

                uid_data.append((
                    f'{rp.mkt}/{rp.rf}',
                    RP,
                    rp.frequency.value,
                    end,
                    start,
                    args.horizon,
                    rp.rp,
                ))
                data.extend(uid_data)

                cal.t0 += BMonthBegin(1)

        except (Ex.MissingData, ValueError, Ex.CalendarError) as ex:
            logger.error(ex)
            logger.info('Stopping the execution for the UID')
            Ut.print_exc(
                Ex.MissingData(
                    f'updateRiskPremiumSeries: Error in processing {index.uid}'
                )
            )
            Ut.print_exc(ex)
            continue

        else:
            logger.info(f'Finished execution for {uid}')

    logger.info(f'Finished all executions, saving to DB...')

    # Save to database
    fields = list(qb.get_fields(_TABLE_))

    # Update/Insert new data
    db.executemany(
        qb.upsert(
            _TABLE_,
            fields=fields
        ),
        data,
        commit=True
    )
    logger.info(f'All done!')
