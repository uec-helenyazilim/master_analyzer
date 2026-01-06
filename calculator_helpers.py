import numpy as np
import pandas as pd
from datetime import datetime

def test_function(**kwargs):
    return 0  
    

def daily_get_group(df: pd.DataFrame):
    """
    Groups dataframe by date and trader_login, sums pnl for each day
    """
    retval = {
        login: None for login in df["trader_login"].unique()
    }
    for login in df["trader_login"].unique():
        login_df = df[df["trader_login"] == login].sort_values(by="time", ascending=False)
        last_daily_report = login_df.iloc[0]
        retval[login] = last_daily_report["group"]

    return retval

def deals_group_by_symbol(deals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups deals by symbol and aggregates profit and volume
    """
    grouped_df = deals_df.groupby("symbol").agg({
        "profit": "sum",
        "volume": "sum",
        "lots": "sum",
        "contract_size": "first",
    }).reset_index()
    return grouped_df

def deals_group_by_login_and_symbol(deals_df: pd.DataFrame) -> pd.DataFrame:
    for login in deals_df["trader_login"].unique():
        # find all symbols for this login
        login_deals_df = deals_df[deals_df["trader_login"] == login]
        grouped_df = deals_group_by_symbol(login_deals_df)
    return grouped_df

def deals_calculate_pnl_per_volume(deals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Requires entry_type, profit, volume columns in deals_df
    """
    # get closed positions deals only
    closing_deals_df = deals_df[deals_df["entry_type"] == "close"]
    retval = pd.DataFrame(columns=["trader_login", "symbol", "total_pnl", "total_volume", "pnl_per_volume"])
    # get total volume
    foo = deals_group_by_login_and_symbol(closing_deals_df)
    
    for login in foo["trader_login"].unique():
        login_deals_df = closing_deals_df[closing_deals_df["trader_login"] == login]
        for symbol in foo["symbol"].unique():
            symbol_deals_df = login_deals_df[login_deals_df["symbol"] == symbol]
            
            total_volume = symbol_deals_df["volume"].sum()
            total_pnl = symbol_deals_df["profit"].sum()
            
            new_row = [login, symbol, total_pnl, total_volume,
                       total_pnl / total_volume if total_volume != 0 else 0]
            retval.iloc[len(retval)] = new_row
    
    return retval

def deals_calculate_pnl_per_trade(deals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Requires entry_type, profit, volume columns in deals_df
    """
    # get closed positions deals only
    closing_deals_df = deals_df[deals_df["entry_type"] == "close"]
    retval = pd.DataFrame(columns=["trader_login", "symbol", "num_deals", "total_pnl", "pnl_per_trade"])
    # get total volume
    foo = deals_group_by_login_and_symbol(closing_deals_df)
    
    for login in foo["trader_login"].unique():
        login_deals_df = closing_deals_df[closing_deals_df["trader_login"] == login]
        for symbol in foo["symbol"].unique():
            symbol_deals_df = login_deals_df[login_deals_df["symbol"] == symbol]
            
            total_pnl = symbol_deals_df["profit"].sum()
            total_trades = len(symbol_deals_df)
            
            new_row = [login, symbol, total_trades, total_pnl, total_pnl / total_trades if total_trades != 0 else 0]
            retval.iloc[len(retval)] = new_row
    
    return retval
    

def positions_get_open_positions(positions_df: pd.DataFrame):


    """
    Filters positions dataframe to return only open positions
    """
    open_positions_df = positions_df[positions_df["open_time"] >= datetime.today()]
    return open_positions_df


    