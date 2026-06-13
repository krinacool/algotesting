import pandas as pd
import pandas_ta as ta

def calculate_supertrend(df, length, factor):
    """
    Calculates Supertrend using pandas-ta.
    df must have 'high', 'low', 'close' columns.
    """
    if len(df) < length:
        return df

    sti = ta.supertrend(df['high'], df['low'], df['close'], length=length, multiplier=factor)
    if sti is not None:
        df = pd.concat([df, sti], axis=1)
        trend_col = f'SUPERTd_{length}_{factor}.0'
        if trend_col not in df.columns:
            trend_cols = [c for c in df.columns if c.startswith('SUPERTd_')]
            if trend_cols:
                trend_col = trend_cols[-1]

        df[f'trend_{length}_{factor}'] = df[trend_col]

    return df

def get_strategy_signals(df, length1=7, factor1=2.1, length2=10, factor2=1.0, use_dual_st=True):
    """
    Generates signals based on Supertrend.
    """
    df = calculate_supertrend(df, length1, factor1)
    if use_dual_st:
        df = calculate_supertrend(df, length2, factor2)

    if len(df) == 0:
        return 'NONE'

    last_row = df.iloc[-1]
    t1 = last_row.get(f'trend_{length1}_{factor1}')

    if use_dual_st:
        t2 = last_row.get(f'trend_{length2}_{factor2}')
        if t1 == 1 and t2 == 1:
            return 'BUY_CALL'
        elif t1 == -1 and t2 == -1:
            return 'BUY_PUT'
    else:
        if t1 == 1:
            return 'BUY_CALL'
        elif t1 == -1:
            return 'BUY_PUT'

    return 'NONE'

def find_nearest_option(option_chain, target_value, select_by='premium'):
    """
    Finds the nearest option in the chain.
    """
    if not option_chain:
        return None

    nearest = None
    min_diff = float('inf')

    for opt in option_chain:
        val = 0
        if select_by == 'premium':
            val = opt.get('lp', 0)
        elif select_by == 'delta':
            val = opt.get('delta', 0)

        diff = abs(val - target_value)
        if diff < min_diff:
            min_diff = diff
            nearest = opt

    return nearest
