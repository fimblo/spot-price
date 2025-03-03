import argparse
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import statistics
import os
import plotly.graph_objects as go
import plotly.io as pio

script_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE=f"{script_dir}/../database/spot_prices.db"
TIMEZONE='Europe/Stockholm'

def output_run_info(cursor: sqlite3.Cursor):
    # Query to get the time, status, and message of up to 2 batch runs
    cursor.execute('''
        SELECT import_dtime, status, message
        FROM batch
        ORDER BY import_dtime ASC
        LIMIT 2
    ''')
    batch_runs = cursor.fetchall()

    # Print batch run information
    print("Batch Runs:")
    for run in batch_runs:
        import_dtime, status, message = run
        print(f"Time: {import_dtime}, Status: {status}, Message: {message}")



def get_spot_price(cursor: sqlite3.Cursor, start: datetime, end: datetime):
    # Query to get spot prices in SEK for the current day
    cursor.execute('''
        SELECT time_start, kWh_SEK, region
        FROM spot_price
        WHERE time_start >= ? AND time_start < ?
    ''', (start.strftime('%Y-%m-%d %H:%m'),
          end.strftime('%Y-%m-%d %H:%m')))

    return cursor.fetchall()


def output_spot_info(spot_prices_with_time: list[any], today_str: str):
    # Extract prices and find min/max with their times
    spot_prices = [row[1] for row in spot_prices_with_time]
    min_time_str , min_price, _  = min(spot_prices_with_time, key=lambda x: x[1])
    max_time_str , max_price, _ = max(spot_prices_with_time, key=lambda x: x[1])
    avg_price = sum(spot_prices) / len(spot_prices)
    median_price = statistics.median(spot_prices)

    min_time = datetime.fromisoformat(min_time_str).strftime("%I%p")
    max_time = datetime.fromisoformat(max_time_str).strftime("%I%p")

    # Print spot price statistics
    print(f"\nSpot Price Statistics for {today_str}:")
    print(f"Min: {float(min_price):.2f} SEK at {min_time}")
    print(f"Max: {float(max_price):.2f} SEK at {max_time}")
    print(f"Average: {avg_price:.2f} SEK")
    print(f"Median: {median_price:.2f} SEK")

    # Create a nice graph
    normalized_prices = [(price - min_price) / (max_price - min_price) for _, price, _ in spot_prices_with_time]
    colors = [f'rgb({255 * norm}, {0}, {255 * (1 - norm)})' for norm in normalized_prices]


    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[time_start for time_start, _, _ in spot_prices_with_time],
        y=[price*100 for _, price, _ in spot_prices_with_time],
        marker_color = colors,
        name='Spot Price'  # Name of the series
    ))

    # Fix layout
    fig.update_layout(
        title=f"Spot Price Statistics for {today_str}",
        xaxis_title='Time',
        yaxis_title='Price in SEK',
        xaxis=dict(
            tick0=today_str + " 00:00",  # Start at 0 o'clock
            dtick=3600000,  # one histogram per hour
            tickformat='%H'
        )
    )
    region = spot_prices_with_time[0][2]
    pio.write_image(fig, f"spot-price-{today_str}-{region}-SEK.png", format='png')



def main(start_time: datetime, end_time: datetime, run_info: bool=False):
    #date stuff
    today = start_time
    tomorrow = end_time
    today_str = today.strftime('%Y-%m-%d')


    # Connect to the SQLite database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if run_info: 
        output_run_info(cursor)

    # Calculate min, max, average, and median
    spot_prices_with_time = get_spot_price(cursor, today, tomorrow)
    if spot_prices_with_time:
        output_spot_info(spot_prices_with_time, today_str)
    else:
        print("\nNo spot prices available for today.")


    # Close the database connection
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Draft summary and png of spot price')
    args = parser.parse_args()

    timezone = ZoneInfo(TIMEZONE)
    today = datetime.now(timezone).date()
    tomorrow = today + timedelta(days=1)  # start of tomorrow

    main(today, tomorrow)