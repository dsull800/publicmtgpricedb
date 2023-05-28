from flask import Flask
from flask_user import roles_required
from app.dash.dash import Dash
import dash_bootstrap_components as dbc
# from decouple import config
from dotenv import load_dotenv

load_dotenv()

from config import BaseConfig

external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    {
        'href': 'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
        'rel': 'stylesheet',
        'integrity': 'sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO',
        'crossorigin': 'anonymous'
    }
]


def create_app():
    server = Flask(__name__, instance_relative_config=False)
    server.config.from_object(BaseConfig)

    register_dashapps(server)
    register_extensions(server)
    register_blueprints(server)

    return server


def register_dashapps(app):
    from app.price_history.layout import layout as prh_layout
    from app.price_history.callbacks import register_callbacks as prh_callbacks

    from app.winners_losers.layout import layout as wl_layout
    from app.winners_losers.callbacks import register_callbacks as wl_callbacks

    # Meta tags for viewport responsiveness
    meta_viewport = {
        "name": "viewport",
        "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

    price_history = Dash(__name__,
                         server=app,
                         url_base_pathname='/premium/price_history/',
                         meta_tags=[meta_viewport],
                         external_stylesheets=external_stylesheets
                         )

    winners_losers = Dash(__name__,
                          server=app,
                          url_base_pathname='/premium/winners_losers/',
                          meta_tags=[meta_viewport],
                          external_stylesheets=external_stylesheets
                          )

    with app.app_context():
        price_history.title = 'Price History'
        price_history.layout = prh_layout
        prh_callbacks(price_history)

        winners_losers.title = 'Winners/Losers'
        winners_losers.layout = wl_layout
        wl_callbacks(winners_losers)

    _protect_dashviews(price_history)
    _protect_dashviews(winners_losers)


def _protect_dashviews(dashapp):
    for view_func in dashapp.server.view_functions:
        if view_func.startswith(dashapp.config.url_base_pathname):
            dashapp.server.view_functions[view_func] = roles_required('subscribed')(
                dashapp.server.view_functions[view_func])


def register_extensions(server):
    from app.extensions import db
    from app.extensions import migrate

    db.init_app(server)
    migrate.init_app(server, db)


def register_blueprints(server):
    from app.webapp import server_bp
    from app.webapp import google_bp

    server.register_blueprint(server_bp)
    server.register_blueprint(google_bp, url_prefix="/login")
