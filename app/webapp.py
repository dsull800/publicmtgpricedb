from flask import Blueprint, redirect, render_template, request, url_for, session, send_from_directory
from flask_login import login_user, logout_user
from flask_user import current_user, login_required, roles_required
from app.extensions import db
from app.models import User, Role
from flask_dance.contrib.google import make_google_blueprint, google
import stripe
import os
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
import requests
from oauthlib.oauth2 import WebApplicationClient
import json
from datetime import datetime
from flask_mail import Message
import traceback
import watchtower
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler())

client = WebApplicationClient(os.environ['GOOGLE_OAUTH_CLIENT_ID'])


def get_google_provider_cfg():
    return requests.get(os.environ['GOOGLE_DISCOVERY_URL']).json()


server_bp = Blueprint('main', __name__)

google_bp = make_google_blueprint(
    client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=["profile", "email"],
    redirect_url="/"
)

# Set up Stripe
stripe.api_key = os.environ['stripe_secret_key']
stripe_public_key = os.environ['stripe_api_key']
endpoint_secret = os.environ['STRIPE_ENDPOINT_SECRET']


@server_bp.route('/')
def index():
    try:
        return render_template("index.html", title='Home Page', env=os.environ)
    except:
        session.clear()
        return render_template("index.html", title='Home Page', env=os.environ)


@server_bp.route('/logout/')
@login_required
def logout():
    logout_user()
    # session.clear()

    return redirect(url_for('main.index'))


@server_bp.route("/stripe_callback")
def stripe_callback():
    session = stripe.checkout.Session.retrieve(request.args.get('session_id'))
    # customer = stripe.Customer.retrieve(session.customer)
    subscription = stripe.Subscription.retrieve(session.subscription)

    client_reference_id = session['client_reference_id']
    stripe_customer_id = session['customer']
    stripe_subscription_id = session['subscription']
    user = User.query.filter_by(id=client_reference_id).first()
    user.stripe_customer_id = stripe_customer_id
    user.stripe_subscription_id = stripe_subscription_id
    user.roles = [Role.query.filter_by(name='subscribed').one()]
    user.unix_time_end = subscription['current_period_end']
    db.session.commit()

    return redirect('/premium/price_history/')


@server_bp.route("/google_login/")
def google_login():
    logger.info('google_login triggered')
    if not google.authorized:
        logger.info('not google_authorized')
        return redirect(url_for("google.login"))

    try:
        resp = google.get("/oauth2/v1/userinfo")
    except TokenExpiredError:
        logger.info('Token Error')
        return redirect(url_for("google.login"))

    assert resp.ok, resp.text
    user_info = resp.json()

    user_email = user_info.get("email", None)
    user_google_id = user_info.get("id", None)
    user = User.query.filter_by(email=user_email).first()

    if not user:
        # Create a new user with the Google information
        from dashapp import user_manager
        user = User(username=user_email, email=user_email, google_id=user_google_id,
                    email_confirmed_at=datetime.now(),
                    password=user_manager.hash_password(os.environ['SECRET_KEY']))
        user.roles = [Role.query.filter_by(name='unsubscribed').one()]
        db.session.add(user)
        db.session.commit()

    else:
        # Link the existing user to their Google account
        user.google_id = user_google_id
        if len(user.roles) == 0:
            user.roles = [Role.query.filter_by(name='unsubscribed').one()]
            user.email_confirmed_at = datetime.now()
        db.session.commit()

    logger.info('login user google_login')
    login_user(user)
    return redirect(url_for("main.index"))


@server_bp.route("/stripe_webhook/", methods=["POST"])
def stripe_webhook():
    from dashapp import mail
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )

    except ValueError as e:
        # Invalid payload
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return "Invalid signature", 400

    logger.info(event["type"])
    session = event['data']['object']

    # client_reference_id = session.get('client_reference_id', None)
    stripe_customer_id = session.get('customer', None)
    stripe_subscription_id = session.get('subscription', None)
    if stripe_subscription_id is None:
        return "Success", 200
    # subscription = stripe.Subscription.retrieve(stripe_subscription_id)

    if event["type"] == "customer.subscription.paused":
        user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
        user.roles = [Role.query.filter_by(name='unsubscribed').one()]
        user.unix_time_end = session.get('current_period_end')
        db.session.commit()

    elif event["type"] == "customer.subscription.resumed":
        user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
        user.roles = [Role.query.filter_by(name='subscribed').one()]
        user.unix_time_end = session.get('current_period_end')
        db.session.commit()


    elif event["type"] == "customer.subscription.deleted":
        user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
        user.roles = [Role.query.filter_by(name='unsubscribed').one()]
        db.session.commit()

    elif event["type"] == "invoice.paid":
        if session.get('status') in ['active', 'trialing']:
            user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
            user.roles = [Role.query.filter_by(name='subscribed').one()]
            db.session.commit()

    elif event["type"] == "invoice.payment_failed":
        # , "invoice.payment_action_required",
        #                    "payment_intent.payment_failed"]:

        try:
            user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
            user.roles = [Role.query.filter_by(name='unsubscribed').one()]

            msg = Message(
                'MTGStocksClone Subscription Error',
                recipients=[
                    f'receiver’{user.email}',
                ]
            )

            msg.body = f'Please review your stripe subscription status:\n {os.environ["stripe_customer_management_url"]}'

            mail.send(msg)
        except Exception as e:
            ## log event
            logger.info(f'failure: {stripe_subscription_id} \n \n {event}')
            logger.info(traceback.format_exc())

    return "Success", 200


@server_bp.route("/login/google/authorized")
def authorized_google_login():
    code = request.args.get("code")
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(os.environ['GOOGLE_OAUTH_CLIENT_ID'], os.environ['GOOGLE_OAUTH_CLIENT_SECRET']),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        user_google_id = userinfo_response.json()["sub"]
        logger.info(user_google_id)
        user_email = userinfo_response.json()["email"]
        user = User.query.filter_by(email=user_email).first()
        if user is None:
            from dashapp import user_manager
            user = User(username=user_email, email=user_email, google_id=user_google_id,
                        email_confirmed_at=datetime.now(),
                        password=user_manager.hash_password(os.environ['SECRET_KEY']))
            user.roles = [Role.query.filter_by(name='unsubscribed').one()]
            db.session.add(user)
            db.session.commit()

        elif user.google_id != user_google_id:  # might be better to check if None
            user.google_id = user_google_id
            logger.info(user.roles)
            if len(user.roles) == 0:
                user.roles = [Role.query.filter_by(name='unsubscribed').one()]
                user.email_confirmed_at = datetime.now()
            db.session.add(user)
            db.session.commit()

        logger.info("logged in pre-authorized")
        login_user(user)
        return redirect(url_for('main.index'))
    else:
        return "User email not available or not verified by Google.", 400


@server_bp.route("/stripe_subscribe/")
@roles_required('unsubscribed')
def subscribe():
    return render_template("subscribe.html", stripe_public_key=stripe_public_key,
                           pricing_table_id=os.environ['pricing_table_id'])


@server_bp.route('/user/profiles/')
@login_required  # Use of @login_required decorator
def user_profile_page():
    # return redirect(url_for('main.user_profile_page'))
    return render_template("user_profile.html", env=os.environ)


@server_bp.route('/unauthorized/')
@login_required  # Use of @login_required decorator
def unauthorized():
    return render_template("unauthorized.html", env=os.environ)

@server_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(server_bp.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
