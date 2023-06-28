
from pya3 import *
import json
from datetime import datetime
from pytz import timezone
from time import sleep
import pandas as pd
import mplfinance as mpf
from alice_blue import AliceBlue

alice = Aliceblue(user_id='AB093838', api_key='cy5uYssgegMaUOoyWy0VGLBA6FsmbxYd0jNkajvBVJuEV9McAM3o0o2yG6Z4fEFYUGtTggJYGu5lgK89HumH3nBLbxsLjgplbodFHDLYeXX0jGQ5CUuGtDvYKSEzWSMk')

print(alice.get_session_id())  # Get Session ID

lp = 0
socket_opened = False
subscribe_flag = False
subscribe_list = []
unsubscribe_list = []
data_list = []  # List to store the received data
df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])  # Initialize an empty DataFrame for storing the data


def socket_open():
    print("Connected")
    global socket_opened
    socket_opened = True
    if subscribe_flag:
        alice.subscribe(subscribe_list)


def socket_close():
    global socket_opened, lp
    socket_opened = False
    lp = 0
    print("Closed")


def socket_error(message):
    global lp
    lp = 0
    print("Error:", message)


def feed_data(message):
    global lp, subscribe_flag, data_list
    feed_message = json.loads(message)
    if feed_message["t"] == "ck":
        print("Connection Acknowledgement status: %s (Websocket Connected)" % feed_message["s"])
        subscribe_flag = True
        print("subscribe_flag:", subscribe_flag)
        print("-------------------------------------------------------------------------------")
        pass
    elif feed_message["t"] == "tk":
        print("Token Acknowledgement status: %s" % feed_message)
        print("-------------------------------------------------------------------------------")
        pass
    else:
        print("Feed:", feed_message)
        if 'lp' in feed_message:
            timestamp = datetime.now(timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S.%f')
            feed_message['timestamp'] = timestamp
            lp = feed_message['lp']
            data_list.append(feed_message)  # Append the received data to the list
        else:
            print("'lp' key not found in feed message.")


# Connect to AliceBlue

# Socket Connection Request
alice.start_websocket(socket_open_callback=socket_open, socket_close_callback=socket_close,
                      socket_error_callback=socket_error, subscription_callback=feed_data, run_in_background=True,
                      market_depth=False)

while not socket_opened:
    pass

# Subscribe to Tata Motors
subscribe_list = [alice.get_instrument_by_token('NSE', 3456)]
alice.subscribe(subscribe_list)
print(datetime.now())
sleep(10)
print(datetime.now())

# Create an empty DataFrame to store the data
df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])

# Create the plot
fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True)

# Update the graph periodically
while True:
    # Check if there is new data
    if len(data_list) > 0:
        # Convert the received data list to a DataFrame
        new_df = pd.DataFrame(data_list)

        # Convert the 'lp' column to numeric format
        new_df['lp'] = pd.to_numeric(new_df['lp'], errors='coerce')

        # Drop rows with missing 'lp' values
        new_df = new_df.dropna(subset=['lp'])

        # Extract the relevant columns (timestamp, lp)
        new_df = new_df[["timestamp", "lp"]]

        # Convert the timestamp column to datetime format
        new_df["timestamp"] = pd.to_datetime(new_df["timestamp"], format='%Y-%m-%d %H:%M:%S.%f')

        # Set the timestamp column as the DataFrame index
        new_df.set_index("timestamp", inplace=True)

        # Append the new data to the existing DataFrame
        df = df.append(new_df)

        data_list = []  # Clear the data list

    # Replot the graph with updated data
    mpf.plot(df, type='candle', style='charles', ax=ax)

    # Show the plot
    mpf.show()

    sleep(5)
