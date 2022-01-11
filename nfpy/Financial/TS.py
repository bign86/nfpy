#
# TS
# High level functions for time series
#

from nfpy.Assets import TyAsset
import nfpy.Calendar as Cal
import nfpy.Math as Math


def beta(asset: TyAsset, benchmark: TyAsset, start: Cal.TyDate = None,
         end: Cal.TyDate = None, w: int = None, log: bool = False) -> tuple:
    """ Returns the beta between the equity and the benchmark index given
        as input. If dates are specified, the beta is calculated on the
        resulting interval (end date excluded). If a window is given, beta
        is calculated rolling.

        Input:
            asset [TyAsset]: asset to calculate the beta for
            benchmark [TyAsset]: usually an index
            start [TyDate]: start date of the series (default: None)
            end [TyDate]: end date of the series (default: None)
            w [int]: window size for rolling calculation (default: None)
            is_log [bool]: it set to True use is_log returns (default: False)

        Output:
            dt [Union[float, pd.Series]]: dates of the regression (None if
                                          not rolling)
            beta [Union[float, pd.Series]]: beta of the regression
            adj_beta [Union[float, pd.Series]]: adjusted beta
            intercept [Union[float, pd.Series]]: intercept of the regression
    """
    if log:
        eq = asset.log_returns
        idx = benchmark.log_returns
    else:
        eq = asset.returns
        idx = benchmark.returns

    return Math.beta(
        eq.index.values,
        eq.values,
        idx.values,
        start=Cal.pd_2_np64(start),
        end=Cal.pd_2_np64(end),
        w=w
    )


def correlation(asset: TyAsset, benchmark: TyAsset, start: Cal.TyDate = None,
                end: Cal.TyDate = None, w: int = None, log: bool = False) \
        -> tuple:
    """ Returns the beta between the equity and the benchmark index given
        as input. If dates are specified, the beta is calculated on the
        resulting interval (end date excluded). If a window is given, beta
        is calculated rolling.

        Input:
            asset [TyAsset]: asset to calculate the beta for
            benchmark [TyAsset]: usually an index
            start [TyDate]: start date of the series (default: None)
            end [TyDate]: end date of the series excluded (default: None)
            w [int]: window size for rolling calculation (default: None)
            is_log [bool]: it set to True use is_log returns (default: False)

        Output:
            dt [Union[float, pd.Series]]: dates of the regression (None if
                                          not rolling)
            beta [Union[float, pd.Series]]: beta of the regression
            intercept [Union[float, pd.Series]]: intercept of the regression
    """
    if log:
        eq = asset.log_returns
        idx = benchmark.log_returns
    else:
        eq = asset.returns
        idx = benchmark.returns

    return Math.correlation(
        eq.index.values,
        eq.values,
        idx.values,
        start=Cal.pd_2_np64(start),
        end=Cal.pd_2_np64(end),
        w=w
    )
