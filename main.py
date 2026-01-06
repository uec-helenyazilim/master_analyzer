from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sys

from src.master_analyzer import MasterAnalyzer


analyzer = MasterAnalyzer()

app = FastAPI(title="Master Analyzer API")


class CollectRequest(BaseModel):
    login_number: Optional[int] = None
    symbol: Optional[str] = None
    start_time: Optional[str] = None  # YYYY-MM-DD
    end_time: Optional[str] = None    # YYYY-MM-DD


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/api/collect")
async def api_collect(payload: CollectRequest):
    try:
        login = payload.login_number
        symbol = (payload.symbol or '').strip() or None

        def parse_date(s: Optional[str]):
            if not s:
                return None
            try:
                return datetime.strptime(s, '%Y-%m-%d')
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid date format for '{s}'. Use YYYY-MM-DD")

        start_dt = parse_date(payload.start_time)
        end_dt = parse_date(payload.end_time)

        deals_df = analyzer.collector.fetch_table_from_view_table(
            'deals', login=login, symbol=symbol, start_time=start_dt, end_time=end_dt
        )
        positions_df = analyzer.collector.fetch_table_from_view_table(
            'positions', login=login, symbol=symbol, start_time=start_dt, end_time=end_dt
        )
        daily_df = analyzer.collector.fetch_table_from_view_table(
            'daily', login=login, start_time=start_dt, end_time=end_dt
        )

        if deals_df is not None:
            analyzer.presenter.place_table('raw_deals_table', deals_df)
        if positions_df is not None:
            analyzer.presenter.place_table('raw_positions_table', positions_df)
        if daily_df is not None:
            analyzer.presenter.place_table('raw_timeframe_daily_table', daily_df)

        return {"status": "ok", "available_tables": list(analyzer.presenter.tables.keys())}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables")
async def api_tables():
    try:
        tables = analyzer.get_dfs_from_presenter()
        html_tables = {name: df.to_html(classes='dataframe', header=True, index=False) for name, df in tables.items()}
        return {"tables": html_tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static frontend assets under /frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


def main():
    pass
    
if __name__ == "__main__":
    main()