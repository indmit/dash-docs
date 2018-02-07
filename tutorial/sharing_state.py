# -*- coding: utf-8 -*-
from textwrap import dedent as s
import dash_core_components as dcc
import dash_html_components as html
from components import Syntax


layout = html.Div([
    html.H1('Sharing State Between Callbacks'),

    dcc.Markdown(s('''
    One of the core Dash principles explained in the
    [Getting Started Guide on Callbacks](https://plot.ly/dash/getting-started-part-2)
    is that **Dash Callbacks must never modify variables outside of their
    scope**. It is not safe to modify any `global` variables.
    This chapter explains why and provides some alternative patterns for
    sharing state between callbacks.

    ## Why Share State?

    In some apps, you may have multiple callbacks that depend on expensive data
    processing tasks like making SQL queries,
    running simulations, or downloading data.

    Rather than have each callback run the same expensive task,
    you can have one callback run the task and then share the
    results to the rest of the callbacks.

    ''')),

    dcc.Markdown(s('''

    ## Why `global` variables will break your app

    Dash is designed to work in multi-user environments
    where multiple people may view the application at the
    same time and will have **independent sessions**.

    If your app uses modified `global` variables,
    then one user's session could set the variable to one value
    which would affect the next user's session.

    Dash is also designed to be able to run with **multiple python
    workers** so that callbacks can be executed in parallel.
    This is commonly done with `gunicorn` using syntax like
    ```
    $ gunicorn --workers 4 --threads 2 app:server
    ```

    When Dash apps run across multiple workers, their memory
    _is not shared_. This means that if you modify a global
    variable in one callback, that modification will not be
    applied to the rest of the workers.

    ***

    ''')),

    Syntax('''df = pd.DataFrame({
    'a': [1, 2, 3],
    'b': [4, 1, 4],
    'c': ['x', 'y', 'z'],
})

app.layout = html.Div([
    dcc.Dropdown(
        id='dropdown',
        options=[{'label': i, 'value': i} for i in df['c'].unique()],
        value='a'
    ),
    html.Div(id='output'),
])

@app.callback(Output('output', 'children'),
              [Input('dropdown', 'value')])
def update_output_1(value):
    # Here, `df` is an example of a variable that is
    # "outside the scope of this function".
    # *It is not safe to modify or reassign this variable
    #  inside this callback.*
    global df = df[df['c'] == value]  # do not do this, this is not safe!
    return len(df)

''', summary='''
    Here is a sketch of an app with a callback that modifies data
    out of it's scope. This type of pattern *will not work reliably*
    for the reasons outlined above.'''),

    Syntax('''df = pd.DataFrame({
    'a': [1, 2, 3],
    'b': [4, 1, 4],
    'c': ['x', 'y', 'z'],
})

app.layout = html.Div([
    dcc.Dropdown(
        id='dropdown',
        options=[{'label': i, 'value': i} for i in df['c'].unique()],
        value='a'
    ),
    html.Div(id='output'),
])

@app.callback(Output('output', 'children'),
              [Input('dropdown', 'value')])
def update_output_1(value):
    # Safely reassign the filter to a new variable
    filtered_df = df[df['c'] == value]
    return len(filtered_df)
''', summary='''
    To fix this example, simply re-assign the filter to a new
    variable inside the callback or follow one of the strategies
    outlined in the next part of this guide.'''),

    dcc.Markdown(s('''
        ## Sharing Data Between Callbacks

        In order for to share data safely across multiple python
        processes, we need to store the data somewhere that is accessible to
        each of the processes. There are 3 places to store this data:

        1 - In the user's browser session

        2 - On the disk (e.g. on a file or on a new database)

        3 - In a shared memory space like with Redis

        The following three examples illustrate these approaches.

        ## Example 1 - Storing Data in Hidden Div

        To save data in user's browser's session:
        - Implemented by saving the data as part of Dash's front-end store
          through methods explained in
          [https://community.plot.ly/t/sharing-a-dataframe-between-plots/6173](https://community.plot.ly/t/sharing-a-dataframe-between-plots/6173)
        - Data has to be converted to a string like JSON for storage and transport
        - Data that is cached in this way will _only be available in the
          user's current session_.
          - If you open up a new browser, the app's callbacks will always
            compute the data. The data is only cached and transported between
            callbacks within the session.
          - As such, unlike with caching, this method doesn't increase the
            memory footprint of the app.
          - There could be a cost in network transport. If your sharing 10MB
            of data between callbacks, then that data will be transported over
            the network between each callback.
           - If the network cost is too high, then compute the aggregations
             upfront and transport those.
             Your app likely won't be displaying 10MB of data,
             it will just be displaying a subset or an aggregation of it.
    ''')),

    Syntax(
        summary=('''
        This example outlines how you can perform an expensive data processing
        step in one callback, serialize the output at JSON, and provide it
        as an input to the other callbacks. This example uses standard dash
        callbacks and stores the JSON-ified data inside a hidden div in
        the app.
    '''), children=s('''
        global_df = pd.read_csv('...')
        app.layout = html.Div([
            dcc.Graph(id='graph'),
            html.Table(id='table'),
            dcc.Dropdown(id='dropdown'),

            # Hidden div inside the app that stores the intermediate value
            html.Div(id='intermediate-value', style={'display': 'none'})
        ])

        @app.callback(Output('intermediate-value', 'children'), [Input('dropdown', 'value')])
        def clean_data(value):
             # some expensive clean data step
             cleaned_df = your_expensive_clean_or_compute_step(value)

             # more generally, this line would be
             # json.dumps(cleaned_df)
             return cleaned_df.to_json(date_format='iso', orient='split')

        @app.callback(Output('graph', 'figure'), [Input('intermediate-value', 'children')])
        def update_graph(jsonified_cleaned_data):

            # more generally, this line would be
            # json.loads(jsonified_cleaned_data)
            dff = pd.read_json(jsonified_cleaned_data, orient='split')

            figure = create_figure(dff)
            return figure

        @app.callback(Output('table', 'children'), [Input('intermediate-value', 'children')])
        def update_table(jsonified_cleaned_data):
            dff = pd.read_json(jsonified_cleaned_data, orient='split')
            table = create_table(dff)
            return table
    ''')),

    dcc.Markdown(s('''
        ***

        ## Example 2 - Computing Aggregations Upfront

        Sending the computed data over the network can be expensive if
        the data is large. In some cases, serializing this data and JSON
        can also be expensive.

        In many cases, your app will only display a subset or an aggregation
        of the computed or filtered data. In these cases, you could precompute
        your aggregations in your data processing callback and transport these
        aggregations to the remaining callbacks.
    ''')),

    Syntax(children=s('''
        @app.callback(
            Output('intermediate-value', 'children'),
            [Input('dropdown', 'value')])
        def clean_data(value):
             # an expensive query step
             cleaned_df = your_expensive_clean_or_compute_step(value)

             # a few filter steps that compute the data
             # as it's needed in the future callbacks
             df_1 = cleaned_df[cleaned_df['fruit'] == 'apples']
             df_2 = cleaned_df[cleaned_df['fruit'] == 'oranges']
             df_3 = cleaned_df[cleaned_df['fruit'] == 'figs']

             datasets = {
                 'df_1': df_1.to_json(orient='split', date_format='iso'),
                 'df_2': df_2.to_json(orient='split', date_format='iso'),
                 'df_3': df_3.to_json(orient='split', date_format='iso'),
             }

             return json.dumps(datasets)

        @app.callback(
            Output('graph', 'figure'),
            [Input('intermediate-value', 'children')])
        def update_graph_1(jsonified_cleaned_data):
            datasets = json.loads(jsonified_cleaned_data)
            dff = pd.read_json(datasets['df_1'], orient='split')
            figure = create_figure_1(dff)
            return figure

        @app.callback(
            Output('graph', 'figure'),
            [Input('intermediate-value', 'children')])
        def update_graph_2(jsonified_cleaned_data):
            datasets = json.loads(jsonified_cleaned_data)
            dff = pd.read_json(datasets['df_2'], orient='split')
            figure = create_figure_2(dff)
            return figure

        @app.callback(
            Output('graph', 'figure'),
            [Input('intermediate-value', 'children')])
        def update_graph_3(jsonified_cleaned_data):
            datasets = json.loads(jsonified_cleaned_data)
            dff = pd.read_json(datasets['df_3'], orient='split')
            figure = create_figure_3(dff)
            return figure
        '''), summary='''Here's a simple example of how you might transport
        filtered or aggregated data to multiple callbacks.
    '''),

    dcc.Markdown(s('''
        ***

        ## Example 3 - Caching and Signaling

        This example:
        - Uses Redis via Flask-Cache for storing “global variables”.
          This data is accessed through a function who’s output is
          cached and keyed by its input arguments.
        - Uses the hidden div solution to send a signal to the other
          callbacks when the expensive computation is complete
        - Note that instead of Redis, you could also save this to the file
          system. See https://flask-caching.readthedocs.io/en/latest/
          for more details.
        - This “signaling” is cool because it allows the expensive
          computation to only take up one process.
          Without this type of signaling, each callback could end up
          computing the expensive computation in parallel,
          locking 4 processes instead of 1.

        This approach also has the advantage that future sessions
        use the pre-computed value.
        This will work well for apps that have a small number of inputs.

        Here’s what this example looks like. Some things to note:

        - I’ve simulated an expensive process by using a time.sleep(5).
        - When the app loads, it takes 5 seconds to render all 4 graphs
        - The initial computation only blocks 1 process
        - Once the computation is complete, the signal is sent and 4 callbacks
          are executed in parallel to render the graphs.
          Each of these callbacks retrieves the data from the
          “global store”: the redis cache.
        - I’ve set processes=6 in app.run_server so that multiple callbacks
          can be executed in parallel. In production, this is done with
          something like $ gunicorn --workers 6 --threads 2 app:server
        - Selecting a value in the dropdown will take less than 5 seconds
          if it has already been selected in the past.
          This is because the value is being pulled from the cache.
        - Similarly, reloading the page or opening the app in a new window
          is also fast because the initial state and the initial expensive
          computation has already been computed.
    ''')),

    html.Div(
        children=html.Img(
            src='https://user-images.githubusercontent.com/1280389/31468665-bf1b6026-aeac-11e7-9388-d9a5e71d964e.gif',
            alt='Example of a Dash App that uses Caching'
        ),
        className="gallery"
    ),

    Syntax(summary="Here's what this example looks like in code",
           children=s('''
        import copy
        import dash
        from dash.dependencies import Input, Output
        import dash_html_components as html
        import dash_core_components as dcc
        import datetime
        from flask_caching import Cache
        import numpy as np
        import os
        import pandas as pd
        import time


        app = dash.Dash(__name__)
        CACHE_CONFIG = {
            # try 'filesystem' if you don't want to setup redis
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'localhost:6379')
        }
        cache = Cache()
        cache.init_app(app.server, config=CACHE_CONFIG)

        N = 100

        df = pd.DataFrame({
            'category': (
                (['apples'] * 5 * N) +
                (['oranges'] * 10 * N) +
                (['figs'] * 20 * N) +
                (['pineapples'] * 15 * N)
            )
        })
        df['x'] = np.random.randn(len(df['category']))
        df['y'] = np.random.randn(len(df['category']))

        app.layout = html.Div([
            dcc.Dropdown(
                id='dropdown',
                options=[{'label': i, 'value': i} for i in df['category'].unique()],
                value='apples'
            ),
            html.Div([
                html.Div(dcc.Graph(id='graph-1'), className="six columns"),
                html.Div(dcc.Graph(id='graph-2'), className="six columns"),
            ], className="row"),
            html.Div([
                html.Div(dcc.Graph(id='graph-3'), className="six columns"),
                html.Div(dcc.Graph(id='graph-4'), className="six columns"),
            ], className="row"),

            # hidden signal value
            html.Div(id='signal', style={'display': 'none'})
        ])


        # perform expensive computations in this "global store"
        # these computations are cached in a globally available
        # redis memory store which is available across processes
        # and for all time.
        @cache.memoize()
        def global_store(value):
            # simulate expensive query
            print('Computing value with {}'.format(value))
            time.sleep(5)
            return df[df['category'] == value]


        def generate_figure(value, figure):
            fig = copy.deepcopy(figure)
            filtered_dataframe = global_store(value)
            fig['data'][0]['x'] = filtered_dataframe['x']
            fig['data'][0]['y'] = filtered_dataframe['y']
            fig['layout'] = {'margin': {'l': 20, 'r': 10, 'b': 20, 't': 10}}
            return fig


        @app.callback(Output('signal', 'children'), [Input('dropdown', 'value')])
        def compute_value(value):
            # compute value and send a signal when done
            global_store(value)
            return value


        @app.callback(Output('graph-1', 'figure'), [Input('signal', 'children')])
        def update_graph_1(value):
            # generate_figure gets data from `global_store`.
            # the data in `global_store` has already been computed
            # by the `compute_value` callback and the result is stored
            # in the global redis cached
            return generate_figure(value, {
                'data': [{
                    'type': 'scatter',
                    'mode': 'markers',
                    'marker': {
                        'opacity': 0.5,
                        'size': 14,
                        'line': {'border': 'thin darkgrey solid'}
                    }
                }]
            })


        @app.callback(Output('graph-2', 'figure'), [Input('signal', 'children')])
        def update_graph_2(value):
            return generate_figure(value, {
                'data': [{
                    'type': 'scatter',
                    'mode': 'lines',
                    'line': {'shape': 'spline', 'width': 0.5},
                }]
            })


        @app.callback(Output('graph-3', 'figure'), [Input('signal', 'children')])
        def update_graph_3(value):
            return generate_figure(value, {
                'data': [{
                    'type': 'histogram2d',
                }]
            })


        @app.callback(Output('graph-4', 'figure'), [Input('signal', 'children')])
        def update_graph_4(value):
            return generate_figure(value, {
                'data': [{
                    'type': 'histogram2dcontour',
                }]
            })


        # Dash CSS
        app.css.append_css({
            "external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
        # Loading screen CSS
        app.css.append_css({
            "external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})

        if __name__ == '__main__':
            app.run_server(debug=True, processes=6)
        '''
    ))

])
