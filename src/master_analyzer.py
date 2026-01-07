from datetime import datetime, timedelta, UTC
from genericpath import isdir
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
import mysql.connector
import warnings
warnings.filterwarnings("ignore")

from . import parser_helpers as parser_helpers
from . import calculator_helpers as calculator_helpers
from . import presenter_helpers as presenter_helpers

columns_to_pull_from_view_tables = {
    # Columns trimmed to match Base table definitions
    'daily': [
        'Login', 'Datetime', 'Group', 'Currency', 'Company', 'Balance', 'Credit', 'InterestRate',
        'CommissionDaily', 'CommissionMonthly', 'BalancePrevDay', 'BalancePrevMonth', 'EquityPrevDay',
        'EquityPrevMonth', 'Margin', 'MarginFree', 'MarginLevel', 'MarginLeverage', 'Profit',
        'ProfitStorage', 'ProfitCommission', 'ProfitEquity', 'DailyProfit', 'DailyBalance',
        'DailyCredit', 'DailyCharge', 'DailyCorrection', 'DailyBonus', 'DailyStorage',
        'DailyCommInstant', 'DailyCommFee', 'DailyCommRound'
    ],
    'deals': [
        'Deal', '`Time`', 'Login', "'Order'", 'Action', 'Entry', 'ContractSize', 'Symbol', 'Price',
        'Profit', 'Commission', 'PricePosition', 'Volume', 'VolumeClosed'
    ],
    'eod_positions': ['login', 'symbol', 'cmd', 'cs', 'date', 'openprice', 'swap', 'profit', 'lot'],
    'positions': [
        'Position_ID', 'Position', 'Login', 'TimeCreate', 'Symbol', 'Action', 'Digits', 
        'DigitsCurrency', 'Reason', 'ContractSize', 'PriceOpen', 'PriceSL', 'PriceTP', 
        'VolumeExt', 'Storage', 'RateMargin', 'Comment', 'Volume'
    ],
    'users': ['Login', 'LastAccess', 'Group', 'CertSerialNumber', 'Rights', 
              'Registration', 'LastAccess', 'LastPassChange', 
              'FirstName', 'LastName', 'MiddleName', 'Company', 'Account', 'Country', 'Language', 
              'ClientID', 'City', 'State', 'ZipCode', 'Address', 'Phone', 'Email', 'ID', 
              'Status', 'Comment', 'Color', 'PhonePassword', 'Leverage', 'Agent', 'TradeAccounts', 
              'LeadCampaign', 'LeadSource', 'TimestampTrade', 
              'Balance', 'Credit', 'InterestRate', 'CommissionDaily', 'CommissionMonthly', 
              'BalancePrevDay', 'BalancePrevMonth', 'EquityPrevDay', 'EquityPrevMonth', 
              'Name', 'MQID', 'LastIP', 'ApiData', 'LimitPositions', 'LimitOrders']
}

time_column_names_for_tables = {
    "daily": "Datetime", # timestamp (1e10)
    "deals": "Time", # YYYY-MM-DD HH:MM:SS
    "eod_positions": "date", # YYYY-MM-DD
    "positions": "TimeCreate", # YYYY-MM-DD HH:MM:SS
    "users": "LastAccess" # YYYY-MM-DD HH:MM:SS
} 



local_db_columns = {
    "daily_data": ['login', 'timestamp', 'group', 'currency', 'company', 'balance', 'credit', 'interest_rate', 'commission_daily', 'commission_monthly', 'balance_prev_day', 'balance_prev_month', 'equity_prev_day', 'equity_prev_month', 'margin', 'margin_free', 'margin_level', 'margin_leverage', 'profit', 'profit_storage', 'profit_commission', 'profit_equity', 'daily_profit', 'daily_balance', 'daily_credit', 'daily_charge', 'daily_correction', 'daily_bonus', 'daily_storage', 'daily_comm_instant', 'daily_comm_fee', 'daily_comm_round'],
    "deals_data": ['deal_id', 'login', 'timestamp', 'dealer', 'order_id', 'action', 'entry', 'reason', 'digits', 'contract_size', 'symbol', 'price', 'volume_ext', 'profit', 'storage', 'commission', 'rate_profit', 'rate_margin', 'position_id', 'comment', 'profit_raw', 'price_position', 'price_sl', 'price_tp', 'volume_closed_ext', 'modify_flags', 'market_bid', 'market_ask', 'market_last', 'volume', 'volume_closed'],
    "positions_data": ['position_id', 'position', 'login', 'timestamp', 'symbol', 'action', 'digits', 'digits_currency', 'reason', 'contract_size', 'price_open', 'price_sl', 'price_tp', 'volume_ext', 'storage', 'rate_margin', 'comment', 'volume']
}

raw_data_details = {
    # table_type: {
    #     "file_path": str | list[str],
    #     "file_type": "csv" | "json",
    #     "timeframe_days": int | None (only for timeframe tables)
    #     }
    "deals_table": {
        "file_path": "C:\\Users\\Uğur Eren\\Desktop\\Edge\\deals_560003.csv",
        "file_type": "csv",
        "timeframe_days": None,
    },
    "positions_table": {
        "file_path": None,
        "file_type": None,
        "timeframe_days": None,
    },
    "timeframe_tables": [
        # {
        #     "file_path": str,
        #     "file_type": "csv" | "json",
        #     "timeframe_days": int
        # }
        
    ],
}

# calculator tables and metrics
calculator_features = {
    # metric_name: {
    #     "features": [list of feature names required],
    #     "function": function to calculate the metric
    # }
    "test_metric": {
        "features": ["positions_from_deals.trader_login", "positions_from_deals.realized_pnl"],
        "function": calculator_helpers.test_function,
    },
}

parsed_data_filters = {
    "deals": ["trader_login", "symbol", "start_time", "end_time"],
    "positions": [],
    "timeframe_reports": [],
}

csv_target_location = "./data/master_analyzer/results/"


def convert_date_to_mt5_timestamp(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    timestamp = int(dt.timestamp())
    if len(str(timestamp)) < 18:
        timestamp *= 10**(18 - len(str(timestamp)))  # convert to nanoseconds
    return timestamp

def convert_mt5_timestamp_to_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp // 1e8).strftime("%Y-%m-%d")

def print_dataframe_properties(
    df: pd.DataFrame,
    name: str | None = None,
    max_rows_with_nulls: int = 5
) -> dict:
    if df is None:
        print(f"{name or 'DataFrame'}: None")
        return {"is_none": True}
    rows, cols = df.shape
    mem_bytes = df.memory_usage(deep=True).sum()
    dtypes = df.dtypes.astype(str)
    nulls_by_col = df.isna().sum()
    nulls_pct_by_col = (nulls_by_col / rows * 100) if rows else nulls_by_col
    empty_strings_by_col = pd.Series(0, index=df.columns)
    for c in df.select_dtypes(include=["object"]).columns:
        empty_strings_by_col[c] = df[c].eq("").sum()
    nulls_by_row = df.isna().sum(axis=1)
    top_null_rows = nulls_by_row.sort_values(ascending=False).head(max_rows_with_nulls)

    print(f"=== DataFrame Properties: {name or ''} ===")
    print(f"- Shape: {rows} rows x {cols} cols")
    print(f"- Memory: {mem_bytes} bytes")
    print(f"- Dtypes:\n{dtypes.to_string()}")
    print(f"- Nulls per column:\n{nulls_by_col.to_string()}")
    print(f"- Nulls % per column:\n{nulls_pct_by_col.round(2).to_string()}")
    if empty_strings_by_col.sum() > 0:
        print(f"- Empty-string counts per column:\n{empty_strings_by_col.to_string()}")
    print(f"- Total nulls: {int(nulls_by_col.sum())}")
    if rows:
        print(f"- Nulls per row (top {len(top_null_rows)}):\n{top_null_rows.to_string()}")

    return {
        "shape": (rows, cols),
        "memory_bytes": int(mem_bytes),
        "dtypes": dtypes.to_dict(),
        "nulls_by_column": nulls_by_col.to_dict(),
        "nulls_pct_by_column": nulls_pct_by_col.to_dict(),
        "empty_strings_by_column": empty_strings_by_col.to_dict(),
        "total_nulls": int(nulls_by_col.sum()),
        "top_rows_by_nulls": top_null_rows.to_dict(),
    }




# -----------------------------------------
# ---------------- CLASSES ----------------
# -----------------------------------------
class Collector:
    """
    Downloads tables and stores them in raw format.
    If a table has not been updated recently, the new data is pulled from the original source.
    If a table requires parsing, it is passed to the Parser.

    """
    def __init__(self):
        
        with open('credentials.json', 'r') as cred_file:
            credentials = json.load(cred_file)
            mysql_credentials = credentials.get("mt5_view", {})
        self.mysql_connector = mysql.connector.connect(**mysql_credentials)

    def fetch_table_from_daily(self, login: int | None = None, start_timestamp: int | None = None, end_timestamp: int | None = None) -> pd.DataFrame:
        foo = columns_to_pull_from_view_tables['daily']
        for col in foo:
            if col == "Group":
                foo.remove(col)
                foo.append("`Group`")
        query = f"SELECT {', '.join(foo)} FROM metatrader5.mt5_daily_v"

        if login is not None or start_timestamp is not None or end_timestamp is not None:
            query += " WHERE "
            if login:
                query += f"Login = {login} AND "
            if start_timestamp:
                query += f"{time_column_names_for_tables['daily']} >= '{start_timestamp}' AND "
            if end_timestamp:
                query += f"{time_column_names_for_tables['daily']} <= '{end_timestamp}' AND "
            query = query.rstrip(" AND ")  # remove trailing AND

        df = pd.read_sql(query, self.mysql_connector)
        df.sort_values(by=time_column_names_for_tables['daily'], inplace=True)
        return df

    def fetch_table_from_deals(self, login: int | None = None, symbol: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None) -> pd.DataFrame:
        
        foo = columns_to_pull_from_view_tables['deals']
        query = f"SELECT {', '.join(foo)} FROM metatrader5.mt5_deals_v"

        if login is not None or start_time is not None or end_time is not None:
            query += " WHERE "
            if login:
                query += f"Login = {login} AND "
            if symbol:
                query += f"Symbol = '{symbol}' AND "
            if start_time:
                query += f"{time_column_names_for_tables['deals']} >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}' AND "
            if end_time:
                query += f"{time_column_names_for_tables['deals']} <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}' AND "
            query = query.rstrip(" AND ")  # remove trailing AND

        df = pd.read_sql(query, self.mysql_connector)
        df.sort_values(by=time_column_names_for_tables['deals'], inplace=True)
        return df

    def fetch_table_from_eod_positions(self, login: int | None = None, symbol: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None) -> pd.DataFrame:
        query = f"SELECT {', '.join(columns_to_pull_from_view_tables['eod_positions'])} FROM metatrader5.mt5_eod_positions_v"

        if login is not None or start_time is not None or end_time is not None:
            query += " WHERE "
            if login:
                query += f"login = {login} AND "
            if symbol:
                query += f"symbol = '{symbol}' AND "
            if start_time:
                query += f"{time_column_names_for_tables['eod_positions']} >= '{start_time}' AND "
            if end_time:
                query += f"{time_column_names_for_tables['eod_positions']} <= '{end_time}' AND "
            query = query.rstrip(" AND ")  # remove trailing AND

        df = pd.read_sql(query, self.mysql_connector)
        df.sort_values(by=time_column_names_for_tables['eod_positions'], inplace=True)
        return df
    
    def fetch_table_from_positions(self, login: int | None = None, symbol: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None) -> pd.DataFrame:
        print("Fetching positions table...")
        fetch_start_time = datetime.now()
        # timestamp is of metatrader format (nanoseconds since epoch)
        query = f"SELECT {', '.join(columns_to_pull_from_view_tables['positions'])} FROM metatrader5.mt5_positions_v"

        if login is not None or start_time is not None or end_time is not None:
            query += " WHERE "
            if login:
                query += f"Login = {login} AND "
            if symbol:
                query += f"Symbol = '{symbol}' AND "
            if start_time:
                query += f"{time_column_names_for_tables['positions']} >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}' AND "
            if end_time:
                query += f"{time_column_names_for_tables['positions']} <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}' AND "
            query = query.rstrip(" AND ")  # remove trailing AND
        
        df = pd.read_sql(query, self.mysql_connector)
        df.sort_values(by=time_column_names_for_tables['positions'], inplace=True)
        print(f"Positions table fetched in {datetime.now() - fetch_start_time}")
        return df

    def fetch_table_from_users(self, login: int | None = None, start_time: datetime | None = None, end_time: datetime | None = None) -> pd.DataFrame:
        
        query = f"SELECT {', '.join(columns_to_pull_from_view_tables['users'])} FROM metatrader5.mt5_users_v"
        if login is not None or start_time is not None or end_time is not None:
            query += " WHERE "
            if login:
                query += f"Login = {login} AND "
            if start_time:
                query += f"{time_column_names_for_tables['users']} >= '{start_time}' AND "
            if end_time:
                query += f"{time_column_names_for_tables['users']} <= '{end_time}' AND "
            query = query.rstrip(" AND ")  # remove trailing AND
            
        df = pd.read_sql(query, self.mysql_connector)
        df.sort_values(by=time_column_names_for_tables['users'], inplace=True)
        return df
    
    def fetch_table_from_view_table(self, table_name: str, login: int | None = None, symbol: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None):
        retval = None
        if table_name == "daily":
            start_timestamp = int(start_time.timestamp()) if start_time else None
            end_timestamp = int(end_time.timestamp()) if end_time else None
            retval = self.fetch_table_from_daily(login, start_timestamp, end_timestamp)
        
        elif table_name == "deals":
            retval = self.fetch_table_from_deals(login, symbol, start_time, end_time)
        
        elif table_name == "eod_positions":
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0) if start_time else None
            end_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0) if end_time else None
            retval = self.fetch_table_from_eod_positions(login, symbol, start_time, end_time)
        
        elif table_name == "positions":
            retval = self.fetch_table_from_positions(login, symbol, start_time, end_time)
        
        elif table_name == "users":
            retval = self.fetch_table_from_users(login, start_time, end_time)
        
        else:
            print(f"Unknown table name: {table_name}")

        return retval


class Parser:
    def __init__(self):
        
        self.raw_data: dict[str, pd.DataFrame | dict[str, pd.DataFrame] | None] = {
            "timeframe_tables": None,
            "positions_table": None,
            "deals_table": None,
        }
        
        self.result_data: dict[str, pd.DataFrame | dict[str, pd.DataFrame] | None] = {
            "timeframe_tables": None,
            "positions_table": None,
            "deals_table": None,
        }
        
        self.column_name_mappings = {
            # "standard_name": "raw_data_column_name"
            TABLE_TYPE: {
                STANDARD_NAME: "" for STANDARD_NAME in parser_helpers.PARSER_STANDART_COLUMN_NAMES[TABLE_TYPE]
            } for TABLE_TYPE in parser_helpers.PARSER_STANDART_COLUMN_NAMES.keys()
        }
        
        self.table_statistics = {
            "raw_data": {
                "timeframe_tables": {},
                "positions_table": {},
                "deals_table": {},
            },
            "result_data": {
                "timeframe_tables": {},
                "positions_table": {},
                "deals_table": {},
            }
        }
        
        self.parsing_routine_functions = [
            "read_raw_data", # populates the raw_data attribute
            "manage_all_raw_data_column_names", # populates the result_data attribute with standardized column names
            "extract_raw_data_statistics", # populates the table_statistics["raw_data"] attribute
            "manage_empty_entries", # manages empty entries in result_data attribute
            "extract_position_summary_from_deals", # generates the dataframe "self.result_data["positions_from_deals"]""
            "extract_deal_stats", # generates the dataframes "self.result_data["deal_stats_per_login_and_symbol"]" and "self.result_data["deal_stats_per_login_summary"]"
        ]

        self.current_routine = []

    def get_function_by_name(self, function_name: str):
        return getattr(self, function_name, None)

    # read raw data from files and place into raw_data attribute
    def place_raw_deals_data(self, raw_deals_data: pd.DataFrame):
        # sort raw deals data by time 
        self.raw_data["deals_table"] = raw_deals_data.copy(deep=True)
        self.raw_data["deals_table"].sort_values(by="time", inplace=True) if "time" in self.raw_data["deals_table"].columns else None

    def place_raw_positions_data(self, raw_positions_data: pd.DataFrame):
        self.raw_data["positions_table"] = raw_positions_data.copy(deep=True)

    def place_raw_timeframe_data(self, timeframe_days: int, raw_timeframe_data: pd.DataFrame):
        if self.raw_data["timeframe_tables"] is None:
            self.raw_data["timeframe_tables"] = {}
        self.raw_data["timeframe_tables"][f"{timeframe_days}_days"] = raw_timeframe_data

    def read_raw_data(self):
        deals_file_path = raw_data_details["deals_table"]["file_path"]
        if deals_file_path:
            print("Reading deals data from local storage...")
            deals_data = pd.read_csv(deals_file_path) if deals_file_path and deals_file_path.endswith('.csv') else None
            print_dataframe_properties(deals_data, name="Deals Data")
            self.place_raw_deals_data(deals_data)
            print("Deals data pulled from local storage.")
        else:
            print("No deals file provided.")

        positions_file_path = raw_data_details["positions_table"]["file_path"]
        if positions_file_path:
            print("Reading positions data from local storage...")
            positions_data = pd.read_csv(positions_file_path) if positions_file_path and positions_file_path.endswith('.csv') else None
            self.place_raw_positions_data(positions_data)
            print_dataframe_properties(positions_data, name="Positions Data")
            print("Positions data pulled from local storage.")
        else:
            print("No positions file provided.")
        
        timeframe_details = raw_data_details["timeframe_tables"]
        if timeframe_details:
            self.raw_data["timeframe_tables"] = {}
            for i in range(len(timeframe_details)):
                timeframe_days = timeframe_details[i]["timeframe_days"]
                print(f"Reading timeframe data for {timeframe_days} days from local storage...")
                timeframe_file_path = timeframe_details[i]["file_path"]
                # Load the raw data from the files
                timeframe_data = pd.read_csv(timeframe_file_path) if timeframe_file_path and timeframe_file_path.endswith('.csv') else None
                self.raw_data["timeframe_tables"][f"{timeframe_days}_days"] = timeframe_data
                print_dataframe_properties(timeframe_data, name=f"Timeframe Data - {timeframe_days} days")
            print("Timeframe data pulled from local storage.")
        else:
            print("No timeframe files provided.")

    
    # extract statistics from tables
    def extract_raw_data_statistics(self):
        # extract statistics for each table
        for table_type in self.raw_data.keys():
            # timeframe tables
            if table_type == "timeframe_tables":
                if self.raw_data["timeframe_tables"] is not None:
                    for timeframe, timeframe_table in self.raw_data["timeframe_tables"].items():
                        stats_for_table = parser_helpers.extract_statistics_from_tables(timeframe_table)
                        self.table_statistics["raw_data"]["timeframe_tables"][timeframe] = stats_for_table
            else:
                if self.raw_data[f"{table_type}"] is not None:
                    raw_table = self.raw_data[f"{table_type}"]
                    stats_for_table = parser_helpers.extract_statistics_from_tables(raw_table)
                    self.table_statistics["raw_data"][f"{table_type}"] = stats_for_table

    def extract_result_data_statistics(self):
        # extract statistics for each table
        for table_type in self.result_data.keys():
            # timeframe tables
            if table_type == "timeframe_tables":
                if self.result_data["timeframe_tables"] is not None:
                    for timeframe, timeframe_table in self.result_data["timeframe_tables"].items():
                        stats_for_table = parser_helpers.extract_statistics_from_tables(timeframe_table)
                        self.table_statistics["result_data"]["timeframe_tables"][timeframe] = stats_for_table
            else:
                if self.result_data[f"{table_type}"] is not None:
                    raw_table = self.result_data[f"{table_type}"]
                    stats_for_table = parser_helpers.extract_statistics_from_tables(raw_table)
                    self.table_statistics["result_data"][f"{table_type}"] = stats_for_table
                
    
    # extract and manage column names
    def manage_column_names(self, table_type: str):
        if table_type == "timeframe_tables":
            timeframe_tables = self.raw_data["timeframe_tables"]
            if timeframe_tables is None:
                print("No raw data for timeframe tables, skipping column management.")
                return
            for timeframe_table_name, timeframe_table in timeframe_tables.items():
                print(f"**Parsing timeframe table: {timeframe_table_name}...")
                parsed_table = pd.DataFrame()
                for standard_column_name, raw_column_name in parser_helpers.PARSER_STANDART_COLUMN_NAMES["timeframe_tables"].items():
                    if raw_column_name in timeframe_table.columns:
                        parsed_table[standard_column_name] = timeframe_table[raw_column_name]
                    else:
                        parsed_table[standard_column_name] = np.nan
                
                self.result_data["timeframe_tables"] = {} if self.result_data["timeframe_tables"] is None else self.result_data["timeframe_tables"]
                self.result_data["timeframe_tables"][f"{timeframe_table_name}_days"] = parsed_table
                
        else: # for deals and positions tables
            if self.raw_data[f"{table_type}"] is not None:
                raw_table = self.raw_data[f"{table_type}"]
                if raw_table is None:
                    return 
                parsed_table = raw_table.copy(deep=True).rename(columns=parser_helpers.PARSER_STANDART_COLUMN_NAMES[f"{table_type}"])
                print(f"**Parsed {table_type} table:\n", parsed_table.head())
                self.result_data[f"{table_type}"] = parsed_table

    def manage_all_raw_data_column_names(self):
        self.manage_column_names("deals_table")
        self.manage_column_names("positions_table")
        self.manage_column_names("timeframe_tables")

    
    # manage empty entries in raw data
    def manage_empty_entries(self):
        for table_type in self.result_data.keys():

            # timeframe tables
            if table_type == "timeframe_tables":
                print("Managing empty entries in timeframe tables...")

                if self.result_data["timeframe_tables"] is not None:
                    for timeframe, timeframe_table in self.result_data["timeframe_tables"].items():
                        
                        # for each column, manage entries
                        for column_name in timeframe_table.columns:
                        
                            # ensure we operate on a Series (handle df[['col']] or nested DataFrame)
                            col_obj = timeframe_table[column_name]
                            if isinstance(col_obj, pd.DataFrame):
                                # if multi-column accidentally selected, pick first column as fallback
                                if col_obj.shape[1] >= 1:
                                    col_series = col_obj.iloc[:, 0]
                                else:
                                    continue
                            else:
                                col_series = col_obj
                            # if numeric, set empty values to average
                            if pd.api.types.is_numeric_dtype(col_series):
                                timeframe_table[column_name] = parser_helpers.set_empty_values_to_average(col_series)

                            # if string/object, set empty values to "Unknown"
                            elif pd.api.types.is_string_dtype(col_series):
                                timeframe_table[column_name] = parser_helpers.set_empty_values_to_given_value(col_series, "Unknown")
            # positions and deals tables
            else:
                print(f"Managing empty entries in {table_type}...")
                
                # for each column, manage entries
                if self.result_data[f"{table_type}"] is not None:
                    
                    result_table = self.result_data[f"{table_type}"]
                    for column_name in result_table.columns:
                        
                        # ensure we operate on a Series (handle df[['col']] selection)
                        col_obj = result_table[column_name]
                        if isinstance(col_obj, pd.DataFrame):
                            if col_obj.shape[1] >= 1:
                                col_series = col_obj.iloc[:, 0]
                            else:
                                continue
                        else:
                            col_series = col_obj

                        # if numeric, set empty values to average
                        if pd.api.types.is_numeric_dtype(col_series):
                            result_table[column_name] = parser_helpers.set_empty_values_to_average(col_series)

                        # if string/object, set empty values to "Unknown"
                        elif pd.api.types.is_string_dtype(col_series):
                            result_table[column_name] = parser_helpers.set_empty_values_to_given_value(col_series, "Unknown")

    # obtain closed positions from deals table
    def extract_position_summary_from_deals(self, 
        trader_login=None, 
        symbol=None, 
        start_time: datetime | None = None,
        end_time: datetime | None = None
        ):

        if self.result_data["deals_table"] is None:
            print("No deals data available to extract closed positions.")
            return None
        res_df = pd.DataFrame(columns=["trader_login", "symbol", "position_id", "volume_opened", "volume_closed",
                                       "contract_size", "net_volume", "raw_profit", "swap", "commission", "fees", 
                                       "realized_pnl", "first_open_time", "last_deal_time"])
        deals_df = self.result_data["deals_table"].copy(deep=True)
        
        # filtering with passed arguments
        deals_df = deals_df[deals_df["trader_login"] == trader_login] if trader_login is not None else deals_df
        deals_df = deals_df[deals_df["symbol"] == symbol] if symbol is not None else deals_df
        deals_df = deals_df[deals_df["time"] >= start_time] if start_time is not None else deals_df
        deals_df = deals_df[deals_df["time"] <= end_time] if end_time is not None else deals_df


        if deals_df is None:
            print("No deals data available to extract closed positions.")
            return None
        
        # obtain unique logins
        all_logins = deals_df["trader_login"].unique().tolist()
        print(f"Extracting positions from deals for {len(all_logins)} many trader logins...")
        for i, login in enumerate(all_logins):
            trader_deals = deals_df[deals_df["trader_login"] == login]
            
            all_trader_positions = trader_deals["position_id"].unique().tolist()
            for position_id in all_trader_positions:
                
                position_deals = trader_deals[trader_deals["position_id"] == position_id]
                position_results = {
                    "trader_login": login,
                    "symbol": "",
                    "position_id": position_id,
                    "volume_opened": 0.0,
                    "volume_closed": 0.0,
                    "contract_size": 0,
                    "net_volume": 0.0,
                    "raw_profit": 0.0,
                    "swap": 0.0,
                    "commission": 0.0,
                    "fees": 0.0,
                    "realized_pnl": 0.0,
                    "first_open_time": None,
                    "last_deal_time": None,
                }
                # check if the first deal for this position is an entry rather than a balance, credit, or adjustment deal
                if position_deals.iloc[0]["position_id"] <= 0 : # if the deal doesn't contain a valid position id
                    continue
                else: # then there's a valid position
                    position_results["symbol"] = position_deals.iloc[0]["symbol"]
                    position_results["contract_size"] = position_deals.iloc[0]["contract_size"]
                    for i, deal_row in position_deals.iterrows():
                        if deal_row["action"] in [0, 1]: # buy or sell
                            position_results["volume_opened"] += deal_row["volume"] if deal_row["entry"] == 0 else 0.0
                            position_results["volume_closed"] += deal_row["volume"] if deal_row["entry"] == 1 else 0.0
                            position_results["net_volume"] += deal_row["volume"]*(2*(0.5 - deal_row["action"]))
                        
                        position_results["raw_profit"] += deal_row["profit"] if deal_row["profit"] else 0.0
                        position_results["swap"] += deal_row["swap"] if deal_row["swap"] else 0.0
                        position_results["commission"] += deal_row["commission"] if deal_row["commission"] else 0.0
                        position_results["fees"] += deal_row["fee"] if deal_row["fee"] else 0.0
                    position_results["realized_pnl"] = position_results["raw_profit"] + position_results["swap"] - position_results["commission"] - position_results["fees"]
                    position_results["first_open_time"] = position_deals.iloc[0]["time"]
                    position_results["last_deal_time"] = position_deals.iloc[-1]["time"]
                    
                res_df.loc[len(res_df)] = position_results
        
            print(f"\rExtracted positions from deals for trader login {login} ({i+1}/{len(all_logins)})")
        self.result_data["positions_from_deals"] = res_df
        return res_df

    # obtain deal statistics per login
    def extract_deal_stats(self, 
        trader_login=None, 
        symbol=None, 
        start_time: datetime | None = None,
        end_time: datetime | None = None
        ):
        try:
            position_summary_df = self.result_data["positions_from_deals"]
            if position_summary_df is None:
                print("No position summary data available to extract deal stats per login.")
                return None
            res_dict = {login: {} for login in position_summary_df["trader_login"].unique().tolist()}
            res_df_login_and_symbol = pd.DataFrame(columns=["trader_login", "symbol", "total_profit", "total_trades", 
                                            "net_volume", "net_lot", "avg_profit_per_trade", "avg_profit_per_lot", 
                                            "first_trade_time", "last_trade_time"])
            res_df_login_summary = pd.DataFrame(columns=["trader_login", "symbols_traded", 
                                                        "total_number_of_trades", "total_profit_all_symbols", 
                                                        "most_profitable_symbol", "profit_from_most_profitable_symbol", 
                                                        "least_profitable_symbol", "profit_from_least_profitable_symbol"])
            
            for i, login in enumerate(position_summary_df["trader_login"].unique().tolist()):
                all_symbols_for_login = position_summary_df[position_summary_df["trader_login"] == login]["symbol"].unique().tolist()    
                for symbol in all_symbols_for_login:
                    # get results per login and symbol
                    symbol_positions = position_summary_df[(position_summary_df["trader_login"] == login) & (position_summary_df["symbol"] == symbol)]
                    total_profit = symbol_positions["realized_pnl"].sum()
                    total_trades = len(symbol_positions)
                    net_volume = symbol_positions["net_volume"].sum()
                    contract_size = symbol_positions["contract_size"].to_numpy()[0] if len(symbol_positions) > 0 else 0
                    net_lot = (net_volume / contract_size) if contract_size > 0 else 0.0
                    avg_profit_per_trade = (total_profit / total_trades) if total_trades > 0 else 0.0
                    avg_profit_per_lot = (total_profit / net_lot) if net_lot > 0 else 0.0
                    
                    # store in res_df_login_and_symbol for later use
                    res_df_login_and_symbol.loc[len(res_df_login_and_symbol)] = {
                        "trader_login": login,
                        "symbol": symbol,
                        "total_profit": total_profit,
                        "total_trades": total_trades,
                        "net_volume": net_volume,
                        "net_lot": net_lot,
                        "avg_profit_per_trade": avg_profit_per_trade,
                        "avg_profit_per_lot": avg_profit_per_lot,
                        "first_trade_time": symbol_positions["first_open_time"].min(),
                        "last_trade_time": symbol_positions["last_deal_time"].max()
                    }
                # after all symbols for login are processed, get stats obtainable from symbol-speficic statistics
                res_df_login_summary.loc[len(res_df_login_summary)] = {
                    "trader_login": login,
                    "symbols_traded": res_df_login_and_symbol[res_df_login_and_symbol["trader_login"] == login]["symbol"].unique().tolist(),
                    "total_number_of_trades": sum(res_df_login_and_symbol[res_df_login_and_symbol["trader_login"] == login]["total_trades"]),
                    "total_profit_all_symbols": sum(res_df_login_and_symbol[res_df_login_and_symbol["trader_login"] == login]["total_profit"]),
                    "most_profitable_symbol": max(all_symbols_for_login, key=lambda s: res_df_login_and_symbol[(res_df_login_and_symbol["trader_login"] == login) & (res_df_login_and_symbol["symbol"] == s)]["total_profit"].iloc[0]),
                    "profit_from_most_profitable_symbol": res_df_login_and_symbol[(res_df_login_and_symbol["trader_login"] == login) & (res_df_login_and_symbol["symbol"] == max(all_symbols_for_login, key=lambda s: res_df_login_and_symbol[(res_df_login_and_symbol["trader_login"] == login) & (res_df_login_and_symbol["symbol"] == s)]["total_profit"].iloc[0]))]["total_profit"].iloc[0],
                    "least_profitable_symbol": min(all_symbols_for_login, key=lambda s: res_df_login_and_symbol[(res_df_login_and_symbol["trader_login"] == login) & (res_df_login_and_symbol["symbol"] == s)]["total_profit"].iloc[0]),
                    "profit_from_least_profitable_symbol": res_df_login_and_symbol[(res_df_login_and_symbol["trader_login"] == login) & (res_df_login_and_symbol["symbol"] == min(all_symbols_for_login, key=lambda s: res_df_login_and_symbol[(res_df_login_and_symbol["trader_login"] == login) & (res_df_login_and_symbol["symbol"] == s)]["total_profit"].iloc[0]))]["total_profit"].iloc[0],
                }
                print(f"\rExtracted deal stats for trader login {login} ({i+1}/{len(position_summary_df['trader_login'].unique().tolist())})", end="")
            self.result_data["deal_stats_per_login_and_symbol"] = res_df_login_and_symbol
            self.result_data["deal_stats_per_login_summary"] = res_df_login_summary
        except Exception as e:
            print(str(e))
    

class Calculator:

    def __init__(self):
        self.base_tables: dict = {}
        self.result_table = None
    
    def place_table(self, table_name: str, table: pd.DataFrame):
        self.base_tables[table_name] = table
        print(f"{table_name} placed in calculator.")

    def get_list_of_tables_to_use(self):

        # get the names of all needed tables from the metrics
        needed_tables = set()
        for metric in calculator_features.values():
            feature_list = metric.get("features", [])
            for feature in feature_list:
                feature_parts = feature.split(".")
                if feature_parts[0] != "timeframe_tables":
                    needed_tables.add(feature_parts[0])
                else:
                    needed_tables.add("timeframe_tables"+ "." + feature_parts[1])  # e.g., timeframe_tables.30_days
        
        # store in attribute for later use
        self.needed_tables = needed_tables
        return list(needed_tables)
    

class Presenter:
    def __init__(self):
        self.tables = {}

    def place_table(self, table_name: str, table: pd.DataFrame):
        self.tables[table_name] = table
        print(f"{table_name} placed in presenter.")

    def export_dataframe(self, df: pd.DataFrame, filename: str = "exported_data.csv"):
        df.to_csv(csv_target_location + "\\" + filename, index=False)
        print(f"Dataframe exported to {csv_target_location}\\{filename}")
    
    def create_plot_for_two_features(self, feature_x: pd.Series, feature_y: pd.Series):
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(1, 1, 1)
        ax.scatter(feature_x, feature_y)
        ax.set_xlabel('Feature X')
        ax.set_ylabel('Feature Y')
        ax.set_title('Scatter Plot of Feature X vs Feature Y')
        ax.grid(True)
        return fig
    
    def create_scatter_with_hue(self, df: pd.DataFrame, x_col: str, y_col: str, hue_col: str | None = None):
        """Scatter plot with optional third feature encoded as color."""
        fig, ax = plt.subplots(figsize=(10, 6))
        if hue_col:
            scatter = ax.scatter(df[x_col], df[y_col], c=df[hue_col], cmap="viridis", alpha=0.8)
            cbar = fig.colorbar(scatter, ax=ax)
            cbar.set_label(hue_col)
        else:
            ax.scatter(df[x_col], df[y_col], alpha=0.8)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f"{x_col} vs {y_col}" + (f" colored by {hue_col}" if hue_col else ""))
        ax.grid(True)
        return fig

    def create_multi_line_plot(self, df: pd.DataFrame, x_col: str, y_cols: list[str]):
        """Line plot for one x-axis feature against multiple y-axis features."""
        fig, ax = plt.subplots(figsize=(12, 6))
        for col in y_cols:
            ax.plot(df[x_col], df[col], label=col)
        ax.set_xlabel(x_col)
        ax.set_ylabel("Value")
        ax.set_title(f"Time series of {', '.join(y_cols)} vs {x_col}")
        ax.legend()
        ax.grid(True)
        return fig

    def create_correlation_heatmap(self, df: pd.DataFrame, feature_cols: list[str]):
        """Heatmap of correlations for selected features."""
        corr = df[feature_cols[0]].corr(df[feature_cols[1]])
        fig, ax = plt.subplots(figsize=(8, 6))
        cax = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
        fig.colorbar(cax, ax=ax, label="Correlation")
        ax.set_xticks(range(len(feature_cols)))
        ax.set_yticks(range(len(feature_cols)))
        ax.set_xticklabels(feature_cols, rotation=45, ha="right")
        ax.set_yticklabels(feature_cols)
        ax.set_title("Feature Correlation Heatmap")
        return fig

    def create_histogram_grid(self, df: pd.DataFrame, feature_cols: list[str], bins: int = 30):
        """Grid of histograms for multiple features."""
        n = len(feature_cols)
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows))
        axes = axes.flatten() if hasattr(axes, "flatten") else [axes]
        for ax, col in zip(axes, feature_cols):
            ax.hist(df[col].dropna(), bins=bins, alpha=0.8, color="steelblue", edgecolor="black")
            ax.set_title(col)
            ax.grid(True)
        for ax in axes[n:]:
            ax.axis("off")
        fig.tight_layout()
        return fig
    

class MasterAnalyzer:
    def __init__(self):
        self.collector = Collector()
        self.parser = Parser()
        self.calculator = Calculator()
        self.presenter = Presenter()

        """ # pull data using collector
        # we need deals, positions, and timeframe tables (only the daily is present for now)
        print("Starting data collection from view tables...")
        login_input = input("Enter trader login to filter by (or press Enter to skip): ")
        login = int(login_input) if login_input.strip() != "" else None
        symbol = input("Enter symbol to filter by (or press Enter to skip): ")
        symbol = symbol.strip() if symbol.strip() != "" else None
        start_time_str = input("Enter start time (YYYY-MM-DD) to filter by (or press Enter to skip): ")
        end_time_str = input("Enter end time (YYYY-MM-DD) to filter by (or press Enter to skip): ")
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d") if start_time_str.strip() != "" else None
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d") if end_time_str.strip() != "" else None
        self.parser.raw_data["deals_table"] = self.collector.fetch_table_from_view_table("deals", login=login, symbol=symbol, start_time=start_time, end_time=end_time)
        self.parser.raw_data["positions_table"] = self.collector.fetch_table_from_view_table("positions", login=login, symbol=symbol, start_time=start_time, end_time=end_time)
        self.parser.raw_data["timeframe_tables"] = {}
        self.parser.raw_data["timeframe_tables"]["daily"] = self.collector.fetch_table_from_view_table("daily", login=login, start_time=start_time, end_time=end_time)

        # push raw df's into presenter for possible viewing later
        self.presenter.place_table("raw_deals_table", self.parser.raw_data["deals_table"])
        self.presenter.place_table("raw_positions_table", self.parser.raw_data["positions_table"])
        self.presenter.place_table("raw_timeframe_daily_table", self.parser.raw_data["timeframe_tables"]["daily"])

 """
        """ # print available functions in parser
        print("Available parser functions:")
        for i, func_name in enumerate(self.parser.parsing_routine_functions):
            print(f"{i} -> {func_name}")
        function_choices = input("Write the numbers of the functions you want to include in the parsing routine, separated by ', ' (e.g., 1, 3, 5), or press Enter to use none: ").split(", ")

        if function_choices != [""]:
            # add functions to parser routine
            for i, func_choice in function_choices:
                self.parser.current_routine.append(self.parser.parsing_routine_functions[int(func_choice)])

            # run parsing routine
            routine_steps_count = 0
            print("Starting parsing routine...")
            while routine_steps_count < len(self.parser.current_routine):
                print(f"\n--- Step {routine_steps_count+1}/{len(self.parser.current_routine)}: {self.parser.current_routine[routine_steps_count]} ---")
                foo = input("Press Enter to continue, or type 'exit' to stop: ")
                if foo.strip().lower() == "exit":
                    break
                step_function = self.parser.get_function_by_name(self.parser.current_routine[routine_steps_count])
                try: 
                    step_function()
                    print(f"--- Step {routine_steps_count+1} completed ---\n")
                    routine_steps_count += 1
                except Exception as e:
                    print(f"Error in parsing step {routine_steps_count+1}=={self.parser.current_routine[routine_steps_count]}: {str(e)}")
            print("Parsing routine completed.")


            # get tables from parser and place into calculator
            needed_tables = self.calculator.get_list_of_tables_to_use()
            for table_name in needed_tables:
                if table_name.startswith("timeframe_tables"):
                    _, timeframe = table_name.split(".")
                    if self.parser.result_data["timeframe_tables"] is not None and timeframe in self.parser.result_data["timeframe_tables"].keys():
                        self.calculator.place_table(table_name, self.parser.result_data["timeframe_tables"][timeframe])
                else:
                    if table_name in self.parser.result_data.keys() and self.parser.result_data[table_name] is not None:
                        self.calculator.place_table(table_name, self.parser.result_data[table_name])
            
            # run calculation routine
            # go over all the metrics and calculate them
            results = {metric_name: [] for metric_name in calculator_features.keys()}
            
            # for each metric:
            metric_count = 0
            while metric_count < len(calculator_features):
                try:
                    metric_name = list(calculator_features.keys())[metric_count]
                    foo = input(f"\nPress Enter to calculate the next metric: {metric_name}, or type 'exit' to stop: ")
                    if foo.strip().lower() == "exit":
                        break    
                    print(f"\nCalculating metric '{metric_name}' ({metric_count+1}/{len(calculator_features)})...")
                    # obtain the calculation pieces
                    function = calculator_features[metric_name]["function"] # function to return the value for the metric
                    feature_names: list[str] = calculator_features[metric_name]["features"] # features required for the calculation
                    feature_values = {feature: [] for feature in feature_names} # dictionary to hold the feature values

                    # gather the features from base tables

                    for feature in feature_names:
                        print("Gathering feature:", feature)
                        table_type, column_name = feature.split(".")
                        if table_type == "timeframe_reports":
                            timeframe, column_name = column_name.split(".")
                            print(f"Table type: {table_type}, Timeframe: {timeframe}, Column: {column_name}\n")
                            feature_values[feature] = self.calculator.base_tables[table_type][f"{timeframe}"][column_name]
                        else:
                            print(f"Table type: {table_type}, Column: {column_name}\n")
                            feature_values[feature] = self.calculator.base_tables[table_type][column_name]

                    # calculate the metric
                    for row_count in range(len(feature_values[feature_names[0]])):
                        feature_values_for_row = {feature: feature_values[feature][row_count] for feature in feature_names}
                        result_value = function(**feature_values_for_row)
                        results[metric_name].append(result_value)
                        print(f"\rRows finished ({row_count + 1}/{len(feature_values[feature_names[0]])}) for metric '{metric_name}'", end="")
                    
                    # move to next metric
                    metric_count += 1
                    print(f"\nMetric '{metric_name}' calculation completed.")
                
                except Exception as e:
                    print(f"Error calculating metric '{metric_name}': {str(e)}")
                
                
                # place results into result table
                foo = list(results.keys())[0]
                self.calculator.result_table = pd.DataFrame(columns=results.keys()) # each column is a metric
                for row_idx in range(len(results[foo])): # for each row
                    new_row = {metric_name: results[metric_name][row_idx] for metric_name in results.keys()}
                    self.calculator.result_table.loc[len(self.calculator.result_table)] = new_row
                    print(f"\rRows added to result table: {row_idx + 1}/{len(results[foo])}", end="")
            
            print("Calculation routine completed.")

            
            # export calculation results
            self.presenter.export_dataframe(self.calculator.result_table, filename="calculation_results.csv")
         """
        

    def list_available_tables(self):
        print("Available Data Tables:")
        for table_type in self.parser.result_data.keys():
            if table_type == "timeframe_tables":
                if self.parser.result_data["timeframe_tables"] is not None:
                    for timeframe in self.parser.result_data["timeframe_tables"].keys():
                        print(f"- Timeframe Table: {timeframe} days")
                    return list(self.parser.result_data["timeframe_tables"].keys())
            else:
                if self.parser.result_data[f"{table_type}"] is not None:
                    print(f"- {table_type.replace('_', ' ').title()} Table")
                    return [table_type]

    def list_available_data(self):
        print("Available Data Tables:")
        for table_type in self.parser.result_data.keys():
            if table_type == "timeframe_tables":
                if self.parser.result_data["timeframe_tables"] is not None:
                    for timeframe in self.parser.result_data["timeframe_tables"].keys():
                        print(f"- Timeframe Table: {timeframe} days")
            else:
                if self.parser.result_data[f"{table_type}"] is not None:
                    print(f"- {table_type.replace('_', ' ').title()} Table")

    def list_available_metrics(self):
        print("Available Calculation Metrics:")
        for metric_name in calculator_features.keys():
            print(f"- {metric_name}")

    def get_parsed_table(self, table_type: str, **filters):
        
        # check if filters have valid keys
        valid_filter_keys = parsed_data_filters[table_type]
        for key in filters.keys():
            if key not in valid_filter_keys:
                print(f"Invalid filter key '{key}' for table type '{table_type}'. Valid keys are: {valid_filter_keys}")
                return None
        
        if table_type == "timeframe_tables":
            if self.parser.result_data["timeframe_tables"] is None:
                print("No timeframe tables available.")
                return None
            timeframe = filters.get("timeframe_days", None)
            if timeframe is None:
                print("No timeframe_days filter provided for timeframe_tables.")
                return None
            table_key = f"{timeframe}_days"
            if table_key not in self.parser.result_data["timeframe_tables"].keys():
                print(f"No timeframe table found for {timeframe} days.")
                return None
            return self.parser.result_data["timeframe_tables"][table_key]
        
        else:
            if self.parser.result_data[f"{table_type}"] is None:
                print(f"No {table_type} table available.")
                return None
            return self.parser.result_data[f"{table_type}"]

    def get_dfs_from_presenter(self):
        print("tables:", self.presenter.tables)
        return self.presenter.tables


def main():
    pass
    
if __name__ == "__main__":
    main()