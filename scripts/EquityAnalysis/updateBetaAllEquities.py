#
# Calculate Beta
# Script to calculate the Beta exposure of an instrument on an index
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
from nfpy.Financial.SeriesStats.Beta import Beta
import nfpy.IO.Utilities as Ut
from nfpy.Session import get_session
from nfpy.Tools import (Exceptions as Ex, get_logger_glob)

__version__ = '0.1'
_TITLE_ = "<<< Update beta series script >>>"

_TABLE_ = 'DerivedSeriesTS'


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
    parser.add_argument('--unlever', action='store_true',
                        help='calculate an unlevered beta')
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
    if args.unlever:
        BETA = dt.get('Beta.Unlevered')
        BETA_ADJ = dt.get('Beta.Adjusted.Unlevered')
        JENSEN = dt.get('Jensen.Unlevered')
        JENSEN_ADJ = dt.get('Jensen.Adjusted.Unlevered')
    else:
        BETA = dt.get('Beta')
        BETA_ADJ = dt.get('Beta.Adjusted')
        JENSEN = dt.get('Jensen')
        JENSEN_ADJ = dt.get('Jensen.Adjusted')
    dtypes = (BETA, BETA_ADJ, JENSEN, JENSEN_ADJ)

    # Parse horizon
    horizon = Cal.Horizon(args.horizon)
    if not horizon.months:
        raise ValueError('updateBetaSeries: horizon must be in either months or years')

    # Take UIDs
    uids = db.execute('SELECT [uid] FROM [Assets] WHERE [type] = "DerivedSeries"').fetchall()

    # Final data
    data = []

    # Loop over UID
    for uid in uids:
        logger.info(f'<<< UID {uid[0]}')
        uid_data = []

        try:
            # Get asset and market index
            asset = af.get(uid[0])
            market = af.get(asset.index)
            max_dt = None

            # Search for the series
            try:
                series = af.get_derived_series(
                    asset1=uid[0],
                    asset2=asset.index,
                    frequency=Cal.Frequency.M,
                    horizon=str(horizon)
                )
            except Ex.MissingData as ex:
                pass

            else:
                max_dt = _fetch_last_date(db, series.uid, dtypes)
            logger.info(f'{asset.uid}|{asset.index} | max date is {max_dt if max_dt is not None else "None"}')

            if max_dt is None:
                # Get prices
                eq_prices = asset.prices
                eq_prices_numpy = eq_prices.to_numpy()
                mkt_prices_numpy = market.prices.to_numpy()

                # Take the starting date of the series, and go one month forward
                # if data are incomplete for the first month.
                min_eq_idx = cutils.next_valid_index(
                    eq_prices_numpy,
                    0, 0,
                    eq_prices_numpy.shape[0] - 1
                )
                min_mkt_idx = cutils.next_valid_index(
                    mkt_prices_numpy,
                    0, 0,
                    mkt_prices_numpy.shape[0] - 1
                )
                min_date = eq_prices.index[max(min_eq_idx, min_mkt_idx)]
                logger.info(f'No previous data found.\n\tEarliest date with data {min_date.strftime("%Y-%m-%d")}')

                cal.t0 = min_date + BMonthBegin(horizon.months + 1)

            else:
                try:
                    cal.t0 = pd.Timestamp(max_dt) + BMonthBegin(1)
                except Ex.CalendarError as ex:
                    Ut.print_exc(Ex.CalendarError('Reached the end of the calendar'))
                    logger.warning('Reached the end of the calendar')
                    continue

        except Ex.MissingData as ex:
            Ut.print_exc(RuntimeError(f'updateRiskPremiumSeries: Error in processing {uid[0]}'))
            Ut.print_exc(ex)
            logger.error(f'updateRiskPremiumSeries: Error in processing {uid[0]}')
            logger.error(ex)
            continue

        logger.info(f'Starting execution at t0={cal.t0.strftime("%Y-%m-%d")}')

        try:
            while cal.t0 <= cal.end:
                logger.info(f't0 {cal.t0.strftime("%Y-%m-%d")}')
                beta = Beta(
                    asset,
                    Cal.Frequency.M,
                    horizon=horizon
                ).beta(unlever=args.unlever)

                start = pd.Timestamp(beta.start).to_pydatetime().date()
                end = pd.Timestamp(beta.end).to_pydatetime().date()

                uid_data.append((
                    f'{beta.uid}/{beta.mkt}',
                    BETA,
                    beta.frequency.value,
                    end,
                    start,
                    args.horizon,
                    beta.beta
                ))
                uid_data.append((
                    f'{beta.uid}/{beta.mkt}',
                    BETA_ADJ,
                    beta.frequency.value,
                    end,
                    start,
                    args.horizon,
                    beta.adj_beta
                ))
                uid_data.append((
                    f'{beta.uid}/{beta.mkt}',
                    JENSEN,
                    beta.frequency.value,
                    end,
                    start,
                    args.horizon,
                    beta.jensen
                ))
                uid_data.append((
                    f'{beta.uid}/{beta.mkt}',
                    JENSEN_ADJ,
                    beta.frequency.value,
                    end,
                    start,
                    args.horizon,
                    beta.adj_jensen
                ))
                data.extend(uid_data)

                try:
                    cal.t0 += BMonthBegin(1)
                except Ex.CalendarError:
                    raise Ex.CalendarError('Reached the end of the calendar')

        except (Ex.MissingData, ValueError, Ex.CalendarError) as ex:
            logger.error(ex)
            logger.info('Stopping the execution for the UID')
            Ut.print_exc(
                Ex.MissingData(
                    f'calculateBeta: Error in processing {asset.uid}'
                )
            )
            Ut.print_exc(ex)
            continue

        else:
            logger.info(f'Finished execution for {uid}')

    logger.info(f'Finished all executions, saving to DB...')

    # Save to database
    fields = list(qb.get_fields(_TABLE_))
    print(fields)

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
