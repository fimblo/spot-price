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

# Connect to the SQLite database
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

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

# Get the current date
timezone = ZoneInfo(TIMEZONE)
today = datetime.now(timezone).date()
today_str = today.strftime('%Y-%m-%d')
tomorrow = datetime.now(timezone).date() + timedelta(days=1)

# Query to get spot prices in SEK for the current day
cursor.execute('''
    SELECT time_start, kWh_SEK
    FROM spot_price
    WHERE time_start >= ? AND time_start < ?
''', (today,tomorrow))

spot_prices_with_time = cursor.fetchall()

# Calculate min, max, average, and median
if spot_prices_with_time:
    # Extract prices and find min/max with their times
    spot_prices = [row[1] for row in spot_prices_with_time]
    min_time_str , min_price  = min(spot_prices_with_time, key=lambda x: x[1])
    max_time_str , max_price = max(spot_prices_with_time, key=lambda x: x[1])
    avg_price = sum(spot_prices) / len(spot_prices)
    median_price = statistics.median(spot_prices)

    min_time = datetime.fromisoformat(min_time_str).strftime("%I%p")
    max_time = datetime.fromisoformat(max_time_str).strftime("%I%p")

    # Print spot price statistics
    print("\nSpot Price Statistics for Today:")
    print(f"Min: {float(min_price):.2f} SEK at {min_time}")
    print(f"Max: {float(max_price):.2f} SEK at {max_time}")
    print(f"Average: {avg_price:.2f} SEK")
    print(f"Median: {median_price:.2f} SEK")

    # Create a nice graph
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[time_start for time_start, _ in spot_prices_with_time],
        y=[price*100 for _, price in spot_prices_with_time],
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
    pio.write_image(fig, "spot_prices_today.png", format='png')

else:
    print("\nNo spot prices available for today.")


# Close the database connection
conn.close()
