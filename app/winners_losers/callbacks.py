import os
import psycopg2
from creds.credentials import host, dbname, user, password
import pandas as pd
from dash.dependencies import Input, Output

PAGE_SIZE = 20


def register_callbacks(app):
    @app.callback(
        [Output('datatable-paging-page-count', 'data'),
         Output('datatable-paging-page-count', "tooltip_data")],
        [Input('datatable-paging-page-count', "page_current"),
         Input('worl', "value")])
    def update_table(page_current, value, page_size=PAGE_SIZE):
        conn = psycopg2.connect(host=host, user=user,
                                password=password, database=dbname)

        cur = conn.cursor()
        if value == 'Winners':
            cur.execute('''SELECT MAX(id) FROM public.slopes''')
            max_id = cur.fetchall()
            max_id = max_id[0][0]
            cur.execute('''SELECT cardname,slope FROM public.slopes WHERE id<=%s AND id>%s''',
                        (max_id - page_current * page_size, max_id - (page_current + 1) * page_size))
            coeftups = cur.fetchall()
            coefdf = pd.DataFrame(coeftups, columns=["cardname", "slope"]).iloc[::-1]
            coefdfdict = coefdf.to_dict('records')
        else:
            cur.execute('''SELECT MIN(id) FROM public.slopes''')
            min_id = cur.fetchall()
            min_id = min_id[0][0]
            cur.execute('''SELECT cardname,slope FROM public.slopes WHERE id>%s AND id<=%s''',
                        (min_id + (page_current - 1) * page_size, min_id + (page_current) * page_size))
            coeftups = cur.fetchall()
            coefdf = pd.DataFrame(coeftups, columns=["cardname", "slope"])
            coefdfdict = coefdf.to_dict('records')

        tooltip_data = []
        for index, row in coefdf.iterrows():
            tooltip_data.append({
                'cardname': {
                    'value': '![Unknown]({})'.format(
                        os.environ['S3_PICS'] + row['cardname'].replace(' ', '+') + '.jpg'
                    ),
                    'type': 'markdown'
                }
            })

        return coefdfdict, tooltip_data
