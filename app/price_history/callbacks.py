import psycopg2
from datetime import datetime
import pytz
import plotly.graph_objs as go
import datetime
from creds.credentials import host, dbname, user, password
from scripts.analyze import create_sage_endpoint
from decouple import config

import numpy as np
import pandas as pd
from datetime import timedelta

import plotly.express as px
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from dash import ctx
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Trigger
import watchtower
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler())

global namerows, predictor
namerows, predictor = create_sage_endpoint(config('ENV'))  # asyncio.run()


def register_callbacks(app):
    @app.callback(Output('ticker', 'options'),
                  Trigger("onload", "children"))
    def populate_namerows(trigger):
        options = [{"label": x[0], "value": x[0]}
                   for x in namerows]
        return options

    @app.callback(Output("scryfallimg", 'src'),
                  Output("scryfallimg", 'style'),
                  Input("ticker", "value"),
                  Input('time-series-chart', 'clickData'),
                  Input('graphstyle', 'value')
                  )
    def scryfall_img(ticker, click, graphstyle):
        update_style = {
            'margin-left': 'auto',
            'margin-right': 'auto',
            'display': 'block',
            'object-fit': 'contain',
        }
        if ctx.triggered_id == 'time-series-chart' and graphstyle == 'MINAVGMED':
            update_style = {'display': 'none'}

        return \
            'https://mtgstocksclonepics.s3.us-west-2.amazonaws.com/' + str(ticker).replace(' ', '+') + '.jpg', \
                update_style

    @app.callback(Output('transaction-table', 'data'),
                  Output('transaction-table', 'columns'),
                  Output('transaction-table', 'style'),
                  Input('time-series-chart', 'clickData'),
                  State('graphstyle', 'value'),
                  State("ticker", "value"),
                  # Input('time-series-chart', 'selectedData'),
                  # Input('time-series-chart', 'hoverData'),
                  prevent_initial_call=True)
    def click_table(click, graphstyle, ticker):  # , select, hover):
        if click is None:
            raise PreventUpdate
        if graphstyle != 'MINAVGMED':
            return None, None, {'display': 'none'}
        if click['points'][0]['curveNumber'] != 0:
            transactions = pd.DataFrame([['N/A', 'N/A']])
            transactions.columns = ['price', 'title']
            return transactions.to_dict('records'), \
                [{"name": i, "id": i} for i in transactions.columns], \
                {'display': 'inline'}
        # raise Exception('click')
        print(f'click {click}')
        # print(f'select {select}')
        # print(f'hover {hover}')
        # raise Exception('triggered')
        conn = psycopg2.connect(host=host, user=user,
                                password=password, database=dbname)

        cur = conn.cursor()

        cur.execute('''SELECT price, title from public.transactions WHERE carddate=%s and cardname=%s LIMIT 10''',
                    (click['points'][0]['x'], ticker))

        transactions = pd.DataFrame(cur.fetchall())
        print(transactions)
        cur.close()

        transactions.columns = ['price', 'title']
        print(transactions.to_dict('records'))

        return transactions.to_dict('records'), \
            [{"name": i, "id": i} for i in transactions.columns], \
            {'display': 'inline'}

    @app.callback(
        Output("time-series-chart", "figure"),
        Input("ticker", "value"), Input("graphstyle", "value"))
    def display_time_series(ticker, graphstyle):
        conn = psycopg2.connect(host=host, user=user,
                                password=password, database=dbname)

        cur = conn.cursor()

        freq = 'D'
        prediction_length = 7

        analyname = (ticker,)

        utc_now = pytz.utc.localize(datetime.datetime.utcnow())
        pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))

        end_dataset = pd.Timestamp(pst_now.date(), freq=freq)

        if graphstyle == 'MINAVGMED':
            cur.execute('''SELECT date,price FROM public.actual_total_goatbot WHERE cardname=%s''', analyname)

            goatbotrows = cur.fetchall()

            goatdf = pd.DataFrame(goatbotrows, columns=["date", "price"]).set_index("date")

            goatdf.index = pd.to_datetime(goatdf.index, infer_datetime_format=True)

            goatdfarr = []

            goatdfarr.append(goatdf)

            goatdfarr[0].columns = ['price' + str(0)]

            cur.execute('''SELECT carddate,AVGE,MED FROM public.precomputed_ebay_prices WHERE cardname=%s''', analyname)

            ebayrows = cur.fetchall()

            ebaydf = pd.DataFrame(ebayrows, columns=["carddate", "AVG", "MED"]).set_index("carddate")
            ebaydf['MINAVGMED'] = ebaydf.apply(lambda row: np.log(np.minimum(row.AVG, row.MED)), axis=1)
            ebaydf = ebaydf.drop(columns=['AVG', 'MED'])
            ebaydf.index = pd.to_datetime(ebaydf.index, infer_datetime_format=True)

            start_date = ebaydf.index.min()

            cur.execute('''SELECT entrydate,ratio FROM public.precomputed_pioneer WHERE cardname=%s''', analyname)

            piotournrows = cur.fetchall()

            piotourndf = pd.DataFrame(piotournrows, columns=["carddate", "pioratio"]).set_index("carddate")
            piotourndf = piotourndf.astype({'pioratio': 'float64'})

            piotourndf.index = pd.to_datetime(piotourndf.index, infer_datetime_format=True)

            missingdatefix = pd.date_range(start='2019-10-15', end=end_dataset)

            piotourndf = piotourndf.reindex(missingdatefix).fillna(0)

            piotourndf.index.name = 'carddate'

            cur.execute('''SELECT entrydate,ratio FROM public.precomputed_modern WHERE cardname=%s''', analyname)

            moderntournrows = cur.fetchall()

            moderntourndf = pd.DataFrame(moderntournrows, columns=["carddate", "modratio"]).set_index("carddate")
            moderntourndf = moderntourndf.astype({'modratio': 'float64'})

            moderntourndf.index = pd.to_datetime(moderntourndf.index, infer_datetime_format=True)

            missingdatefix = pd.date_range(start='2019-10-15', end=end_dataset)

            moderntourndf = moderntourndf.reindex(missingdatefix).fillna(0)

            moderntourndf.index.name = 'carddate'

            cur.execute('''SELECT entrydate,ratio FROM public.precomputed_standard WHERE cardname=%s''', analyname)

            standardtournrows = cur.fetchall()

            if len(standardtournrows) == 0:
                standardtourndf = pd.DataFrame([['2020-04-03', 0], ['2020-04-04', 0]],
                                               columns=["carddate", "standratio"]).set_index("carddate")
            else:
                standardtourndf = pd.DataFrame(standardtournrows, columns=["carddate", "standratio"]).set_index(
                    "carddate")

            standardtourndf = standardtourndf.astype({'standratio': 'float64'})
            standardtourndf.index = pd.to_datetime(standardtourndf.index, infer_datetime_format=True)

            missingdatefix = pd.date_range(start='2019-10-15', end=end_dataset)

            standardtourndf = standardtourndf.reindex(missingdatefix).fillna(0)

            standardtourndf.index.name = 'carddate'

            goatdfarr.insert(0, ebaydf)
            goatdfarr.append(piotourndf)
            goatdfarr.append(moderntourndf)
            goatdfarr.append(standardtourndf)
            overalldf = pd.concat(goatdfarr, axis=1, sort=True)

            noNaNseries = overalldf['MINAVGMED']

            overalldf = pd.concat([overalldf['MINAVGMED'].fillna("NaN"),
                                   overalldf.loc[:, overalldf.columns.difference(['MINAVGMED'])]
                                  .fillna(method='ffill').fillna(method='bfill')],
                                  axis=1, join='inner')

            dynamic_feat_arr_series = []

            for col in overalldf.columns[1:]:
                dynamic_feat_arr_series.append(
                    list(overalldf[start_date - timedelta(days=prediction_length):end_dataset][col]))

            noNaNseries = noNaNseries[noNaNseries.index >= ebaydf.index.min()].dropna()

            fig = go.Figure()

            fig.add_trace(go.Scatter(x=np.exp(noNaNseries).index, y=np.exp(noNaNseries).values, mode='lines+markers',
                                     connectgaps=False,
                                     marker=dict(size=3.5)
                                     , name='<b>Ebay Price</b>'
                                     ))

            try:
                global namerows, predictor
                args = {
                    "ts": overalldf[start_date:end_dataset]['MINAVGMED'].astype('float64').asfreq(freq),
                    "return_samples": False,
                    "dynamic_feat": dynamic_feat_arr_series,
                    "quantiles": [0.05, 0.5, 0.85],
                    "num_samples": 100,
                    "cat": namerows.index(analyname)
                }
                sage_preds = np.exp(predictor.predict(**args))

                fig.add_trace(go.Scatter(x=sage_preds.index, y=sage_preds['0.5'].values,
                                         connectgaps=True
                                         , name='<b>Predictions</b>'
                                         ))
                fig.add_trace(go.Scatter(x=sage_preds.index, y=sage_preds['0.05'].values,
                                         connectgaps=True
                                         , name='<b>Predictions Lower</b>'
                                         ))
                fig.add_trace(go.Scatter(x=sage_preds.index, y=sage_preds['0.85'].values,
                                         connectgaps=True
                                         , name='<b>Predictions Upper</b>'
                                         ))
            except Exception as e:
                newnamerows, newpredictor = create_sage_endpoint(config('ENV'))  # asyncio.run()
                namerows = newnamerows
                predictor = newpredictor
                logger.exception('attempt to make new endpoint')
                return fig

        elif graphstyle == 'price0':

            cur.execute('''SELECT MIN(carddate) FROM public.precomputed_ebay_prices WHERE cardname=%s''',
                        analyname)

            min_stuff = cur.fetchall()

            cur.execute('''SELECT date,price FROM actual_total_goatbot WHERE cardname=%s''',
                        analyname)

            goatbotrows = cur.fetchall()

            goatdf = pd.DataFrame(goatbotrows, columns=["carddate", "price0"]).set_index("carddate")

            goatdf.index = pd.to_datetime(goatdf.index, infer_datetime_format=True)

            goatdfarr = []

            goatdfarr.append(goatdf)

            goatdfarr[0].columns = ['price' + str(0)]

            goatdf = pd.concat(goatdfarr, axis=1, sort=True)

            goatdf = goatdf[goatdf.index >= min_stuff[0][0]]

            fig = px.line(goatdf, y=graphstyle, labels={'price0': ' '})

        elif graphstyle == 'pioratio':
            cur.execute('''SELECT entrydate,ratio FROM public.precomputed_pioneer WHERE cardname=%s''', analyname)

            piotournrows = cur.fetchall()

            piotourndf = pd.DataFrame(piotournrows, columns=["carddate", "pioratio"]).set_index("carddate")
            piotourndf = piotourndf.astype({'pioratio': 'float64'})

            piotourndf.index = pd.to_datetime(piotourndf.index, infer_datetime_format=True)

            missingdatefix = pd.date_range(start='2019-10-15', end=end_dataset)

            piotourndf = piotourndf.reindex(missingdatefix).fillna(0)

            piotourndf.index.name = 'carddate'

            cur.execute('''SELECT MIN(carddate) FROM public.precomputed_ebay_prices WHERE cardname=%s''',
                        analyname)

            min_stuff = cur.fetchall()

            piotourndf = piotourndf[piotourndf.index >= min_stuff[0][0]]

            fig = px.line(piotourndf, y=graphstyle, labels={'pioratio': ' '})
        elif graphstyle == 'modratio':
            cur.execute('''SELECT entrydate,ratio FROM public.precomputed_modern WHERE cardname=%s''', analyname)

            moderntournrows = cur.fetchall()

            moderntourndf = pd.DataFrame(moderntournrows, columns=["carddate", "modratio"]).set_index("carddate")
            moderntourndf = moderntourndf.astype({'modratio': 'float64'})

            moderntourndf.index = pd.to_datetime(moderntourndf.index, infer_datetime_format=True)

            missingdatefix = pd.date_range(start='2019-10-15', end=end_dataset)

            moderntourndf = moderntourndf.reindex(missingdatefix).fillna(0)

            moderntourndf.index.name = 'carddate'

            cur.execute('''SELECT MIN(carddate) FROM public.precomputed_ebay_prices WHERE cardname=%s''',
                        analyname)

            min_stuff = cur.fetchall()

            moderntourndf = moderntourndf[moderntourndf.index >= min_stuff[0][0]]

            fig = px.line(moderntourndf, y=graphstyle, labels={'modratio': ' '})
        elif graphstyle == 'standratio':
            cur.execute('''SELECT entrydate,ratio FROM public.precomputed_standard WHERE cardname=%s''', analyname)

            standardtournrows = cur.fetchall()

            if len(standardtournrows) == 0:

                standardtourndf = pd.DataFrame([['2000-04-03', 0], ['2000-04-04', 0]],
                                               columns=["carddate", "standratio"]).set_index("carddate")
            else:
                standardtourndf = pd.DataFrame(standardtournrows, columns=["carddate", "standratio"]).set_index(
                    "carddate")

            standardtourndf = standardtourndf.astype({'standratio': 'float64'})
            standardtourndf.index = pd.to_datetime(standardtourndf.index, infer_datetime_format=True)

            missingdatefix = pd.date_range(start='2019-10-15', end=end_dataset)

            standardtourndf = standardtourndf.reindex(missingdatefix).fillna(0)

            standardtourndf.index.name = 'carddate'

            cur.execute('''SELECT MIN(carddate) FROM public.precomputed_ebay_prices WHERE cardname=%s''',
                        analyname)

            min_stuff = cur.fetchall()

            standardtourndf = standardtourndf[standardtourndf.index >= min_stuff[0][0]]
            fig = px.line(standardtourndf, y=graphstyle, labels={'standratio': ' '})

        return fig
