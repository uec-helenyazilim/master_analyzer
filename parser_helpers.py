from datetime import datetime
import pandas as pd
import numpy as np

PARSER_STANDART_COLUMN_NAMES = {
    "timeframe_tables": { # 74 columns
        # Identification & Timeframe
        "report_date": datetime,
        "timeframe_days": int,
        "trader_login": int,
        "account_group": str,
        "account_type": str,
        "server_name": str,
        
        # P&L Metrics
        "total_pnl": float,
        "realized_pnl": float,
        "unrealized_pnl": float,
        "net_profit": float,
        "commission_paid": float,
        "swap_paid": float,
        "fees_total": float,
        
        # Performance Ratios
        "profit_factor": float,
        "sharpe_ratio": float,
        "sortino_ratio": float,
        "calmar_ratio": float,
        "recovery_factor": float,
        "expected_payoff": float,
        
        # Trade Statistics
        "total_trades": int,
        "winning_trades": int,
        "losing_trades": int,
        "breakeven_trades": int,
        "win_rate": float,
        "loss_rate": float,
        "average_win": float,
        "average_loss": float,
        "largest_win": float,
        "largest_loss": float,
        "average_trade_pnl": float,
        "median_trade_pnl": float,
        
        # Position Metrics
        "total_volume": float,
        "total_lots_traded": float,
        "average_position_size": float,
        "max_position_size": float,
        "min_position_size": float,
        
        # Duration Metrics
        "average_trade_duration_minutes": float,
        "average_winning_trade_duration_minutes": float,
        "average_losing_trade_duration_minutes": float,
        "longest_trade_duration_minutes": float,
        "shortest_trade_duration_minutes": float,
        
        # Drawdown Metrics
        "max_drawdown": float,
        "max_drawdown_percent": float,
        "max_drawdown_duration_days": int,
        "current_drawdown": float,
        "max_consecutive_wins": int,
        "max_consecutive_losses": int,
        
        # Balance & Equity
        "starting_balance": float,
        "ending_balance": float,
        "balance_change": float,
        "balance_change_percent": float,
        "peak_balance": float,
        "lowest_balance": float,
        "starting_equity": float,
        "ending_equity": float,
        "equity_change": float,
        "equity_change_percent": float,
        
        # Risk Metrics
        "margin_used": float,
        "margin_free": float,
        "margin_level": float,
        "max_margin_used": float,
        "average_leverage": float,
        "max_leverage_used": float,
        
        # Symbol-Specific
        "symbols_traded": list[str],
        "most_traded_symbol": str,
        "most_profitable_symbol": str,
        "least_profitable_symbol": str,
        
        # Trading Activity
        "trading_days": int,
        "active_trading_days": int,
        "inactive_days": int,
        "trades_per_day": float,
        "average_daily_pnl": float,
        "best_day_pnl": float,
        "worst_day_pnl": float,
     },
    
    "positions_table": { # 48 columns
        # Position Identification
        "position_id": int,
        "ticket": int,
        "trader_login": int,
        "account_group": str,
        "server_name": str,
        
        # Position Details
        "symbol": str,
        "position_type": str,
        "direction": str,
        "volume": float,
        "lots": float,
        "contract_size": float,
        
        # P&L Information
        "unrealized_pnl": float,
        "profit": float,
        
        # Position Costs
        "commission": float,
        "swap": float,
        "total_fees": float,
        "storage_fee": float,
        
        # Margin & Leverage
        "leverage": float,
        "margin_percent": float,
        
        # Duration
        "duration_seconds": int,
        
        # Status
        "position_status": str,
        "is_hedged": bool,
        "last_modification_time": str,
        
        # Account State at Entry
        "account_balance_at_open": float,
        "account_equity_at_open": float,
        "margin_level_at_open": float,
    },
    
    "deals_table": { 
        # Deal Identification
        # keys are standard names, values are the raw column names 
        # currently the raw column names come from mt5_deals_v table
        # Deal	Timestamp	ExternalID	Login	Dealer	Order	Action	Entry	Reason	Digits	DigitsCurrency	ContractSize	Time	TimeMsc	
        "Deal": "deal_id",
        "Timestamp": "timestamp",
        "ExternalID": "external_id",
        "Login": "trader_login",
        "PositionID": "position_id",
        "Dealer": "dealer",
        "Order": "order_id",
        "Action": "action",
        "Entry": "entry",
        "Reason": "reason",
        "Digits": "digits",
        "DigitsCurrency": "digits_currency",
        "ContractSize": "contract_size",
        "Time": "time",
        "TimeMsc": "time_msc",
        # Symbol	Price	VolumeExt	Profit	Storage	Commission	Fee	RateProfit	RateMargin	ExpertID	PositionID	
        "Symbol": "symbol",
        "Price": "price",
        "VolumeExt": "volume",
        "Profit": "profit",
        "Storage": "swap",
        "Commission": "commission",
        "Fee": "fee",
        "RateProfit": "rate_profit",
        "RateMargin": "rate_margin",
        "ExpertID": "expert_id",
        # Comment	ProfitRaw	PricePosition	PriceSL	PriceTP	VolumeClosedExt	TickValue	TickSize	Flags	Gateway	PriceGateway	
        "Comment": "comment",
        "ProfitRaw": "profit_raw",
        "PricePosition": "price_position",
        "PriceSL": "price_sl",
        "PriceTP": "price_tp",
        "VolumeClosedExt": "volume_closed_ext",
        "TickValue": "tick_value",
        "TickSize": "tick_size",
        "Flags": "flags",
        "Gateway": "gateway",
        "PriceGateway": "price_gateway",
        # ModifyFlags	MarketBid	MarketAsk	MarketLast	Volume	VolumeClosed	ApiData	Value	VolumeGatewayExt	ActionGateway	PartyID
        "ModifyFlags": "modify_flags",
        "MarketBid": "market_bid",
        "MarketAsk": "market_ask",
        "MarketLast": "market_last",
        "Volume": "volume",
        "VolumeClosed": "volume_closed",
        "ApiData": "api_data",
        "Value": "value",
        "VolumeGatewayExt": "volume_gateway_ext",
        "ActionGateway": "action_gateway",
        "PartyID": "party_id"
    }
}

def convert_mt5_timestamp_to_datetime(timestamp_microseconds):
    """Convert MT5 timestamp (microseconds) to datetime."""
    return pd.to_datetime(timestamp_microseconds / pow(10,6), unit='s')

def convert_datetime_to_mt5_timestamp(dt: datetime):
    """Convert datetime to MT5 timestamp (microseconds)."""
    zero = datetime(1970, 1, 1)
    delta = dt - zero
    return int(delta.total_seconds() * 1_000_000)


def set_empty_values_to_average(column: pd.Series):
    
    total = 0.0
    count = 0
    for value in column:
        if not pd.isna(value):
            total += value
            count += 1
    average = total / count if count > 0 else 0.0
    return column.apply(lambda x: average if pd.isna(x) else x)

def set_empty_values_to_mode(column: pd.Series):
    counts = {}
    for value in column:
        if not pd.isna(value):
            counts[value] = counts.get(value, 0) + 1

    if not counts:
        mode = np.nan
    else:
        mode = np.max(counts, key=counts.get)

    return column.apply(lambda x: mode if pd.isna(x) else x)

def set_empty_values_to_median(column: pd.Series):
    non_empty_values = [x for x in column if not pd.isna(x)]
    median = np.median(non_empty_values) if non_empty_values else 0.0

    return column.apply(lambda x: median if pd.isna(x) else x)

def set_empty_values_to_given_value(column: pd.Series, value):
    return column.apply(lambda x: value if pd.isna(x) else x)

def extract_statistics_from_tables(df: pd.DataFrame) -> dict:      
        retval = {
            "numeric_columns": [],
            "table_statistics": {}
        }
        # find numeric columns
        retval["numeric_columns"] = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for i, column in enumerate(retval["numeric_columns"]):
            print(r"Extracting statistics for column {}/{}: {}".format(i+1, len(retval["numeric_columns"]), column))
            col_data = df[column]
            non_missing_count = 0
            for i in range(len(col_data)):
                if not pd.isnull(col_data[i]):
                    non_missing_count += 1
            retval["table_statistics"][column] = {
                "non_missing_count": non_missing_count,
                "total_count": len(col_data),
                "mean": col_data.mean(),
                "median": col_data.median(),
                "std_dev": col_data.std(),
                "min": col_data.min(),
                "max": col_data.max()
            }

        return retval
    



