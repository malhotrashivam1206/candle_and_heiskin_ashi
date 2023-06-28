import json
from datetime import datetime
from pytz import timezone
from time import sleep
import pandas as pd
import dash
from dash import dcc
from dash import html
from dash.dependencies import Output, Input
import plotly.graph_objects as go
from alice_blue import AliceBlue
from pya3 import *

# Replace 'YOUR_USER_ID' and 'YOUR_API_KEY' with your AliceBlue user ID and API key
alice = Aliceblue(user_id='AB093838', api_key='cy5uYssgegMaUOoyWy0VGLBA6FsmbxYd0jNkajvBVJuEV9McAM3o0o2yG6Z4fEFYUGtTggJYGu5lgK89HumH3nBLbxsLjgplbodFHDLYeXX0jGQ5CUuGtDvYKSEzWSMk')
print(alice.get_session_id())  # Get Session ID

lp = 0
socket_opened = False
subscribe_flag = False
subscribe_list = []
unsubscribe_list = []
data_list = []  # List to store the received data
df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])  # Initialize an empty DataFrame for storing the data

# File paths for saving data and graph
data_file_path = "ohlc_data-MCX.csv"
graph_file_path = "candlestick_graph-MCX.html"

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

# Subscribe to a symbol/token (replace 'NSE' and 'RELIANCE' with your desired market segment and symbol)
subscribe_list = [alice.get_instrument_by_token('MCX', 252453)]
alice.subscribe(subscribe_list)
print(datetime.now())
sleep(10)
print(datetime.now())

# Create an empty figure for the animated candlestick graph
fig = go.Figure()

# Initialize Dash app
app = dash.Dash(__name__)

# Define the layout of the Dash app
app.layout = html.Div([
    html.H1("Live Candlestick Graph", style={'textAlign': 'center'}),
    dcc.Graph(id='live-graph', config={'displayModeBar': False}),
    dcc.Interval(id='graph-update-interval', interval=200, n_intervals=0)
], style={'height': '100vh'})

# Define the callback function to update the graph
@app.callback(Output('live-graph', 'figure'),
              Input('graph-update-interval', 'n_intervals'))
def update_graph(n):
    global df, data_list

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

        # Save the new data to CSV file
        df.to_csv(data_file_path)

        data_list = []  # Clear the data list

    # Update the candlestick graph with the latest data
    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                         open=df['open'],
                                         high=df['high'],
                                         low=df['low'],
                                         close=df['close'],
                                         increasing_line_color='green',
                                         decreasing_line_color='red',
                                         increasing_fillcolor='rgb(0, 146, 71)',
                                         decreasing_fillcolor='rgba(255,0,0,0.8)',
                                         line_width=1,
                                         opacity=1,
                                         showlegend=False)])

    return fig

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
