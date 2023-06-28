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

alice = Aliceblue(user_id='AB093838', api_key='cy5uYssgegMaUOoyWy0VGLBA6FsmbxYd0jNkajvBVJuEV9McAM3o0o2yG6Z4fEFYUGtTggJYGu5lgK89HumH3nBLbxsLjgplbodFHDLYeXX0jGQ5CUuGtDvYKSEzWSMk')

print(alice.get_session_id())  # Get Session ID

lp = 0
socket_opened = False
subscribe_flag = False
subscribe_list = []
unsubscribe_list = []
data_list = []  # List to store the received data
df = pd.DataFrame(columns=["timestamp", "lp"])  # Initialize an empty DataFrame for storing the data

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

# Subscribe to Tata Motors
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
    dcc.Graph(id='live-candlestick-graph', config={'displayModeBar': False}),
    dcc.Dropdown(
        id='chart-type-dropdown',
        options=[
            {'label': 'Normal', 'value': 'normal'},
            {'label': 'Heikin Ashi', 'value': 'heikin_ashi'},
        ],
        value='normal',
        clearable=False,
        style={'width': '150px'}
    ),
    dcc.Dropdown(
        id='interval-dropdown',
        options=[
            {'label': '5 Sec', 'value': 5},
            {'label': '30 Sec', 'value': 30},
            {'label': '1 Min', 'value': 1},
            {'label': '3 Min', 'value': 3},
            {'label': '5 Min', 'value': 5},
            {'label': '10 Min', 'value': 10},
            {'label': '30 Min', 'value': 30},
            {'label': '60 Min', 'value': 60},
            {'label': '1 Day', 'value': 1440}
        ],
        value=1,
        clearable=False,
        style={'width': '150px'}
    ),
    dcc.Interval(id='graph-update-interval', interval=200, n_intervals=0)
], style={'height': '100vh'})

# Define the callback function to update the graph
@app.callback(Output('live-candlestick-graph', 'figure'),
              Input('graph-update-interval', 'n_intervals'),
              Input('interval-dropdown', 'value'),
              Input('chart-type-dropdown', 'value'))
def update_graph(n, interval, chart_type):
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

    # Resample the data into OHLC format using the selected interval
    resampled_data = df["lp"].resample(f'{interval}T').ohlc()

    # Update the candlestick graph based on the chart type
    if chart_type == 'normal':
        fig = go.Figure(data=[go.Candlestick(x=resampled_data.index,
                                             open=resampled_data['open'],
                                             high=resampled_data['high'],
                                             low=resampled_data['low'],
                                             close=resampled_data['close'],
                                             increasing_line_color='green',
                                             decreasing_line_color='red',
                                             increasing_fillcolor='rgb(0, 146, 71)',
                                             decreasing_fillcolor='rgba(255,0,0,0.8)',
                                             line_width=1,
                                             opacity=1,
                                             showlegend=False)])
    elif chart_type == 'heikin_ashi':
        ha_open = (resampled_data['open'].shift(1) + resampled_data['close'].shift(1)) / 2
        ha_close = (resampled_data['open'] + resampled_data['high'] + resampled_data['low'] + resampled_data[
            'close']) / 4
        ha_high = resampled_data[['open', 'close', 'high']].max(axis=1)
        ha_low = resampled_data[['open', 'close', 'low']].min(axis=1)

        fig = go.Figure(data=[go.Candlestick(x=resampled_data.index,
                                             open=ha_open,
                                             high=ha_high,
                                             low=ha_low,
                                             close=ha_close,
                                             increasing_line_color='green',
                                             decreasing_line_color='red',
                                             increasing_fillcolor='rgb(0, 146, 71)',
                                             decreasing_fillcolor='rgba(255,0,0,0.8)',
                                             line_width=1,
                                             opacity=1,
                                             showlegend=False)])

    # Save the graph as an HTML file
    fig.write_html(graph_file_path)

    return fig

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)