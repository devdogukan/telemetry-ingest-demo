from flask import Flask

from flask_app.routes import regiter_routes

def create_app():
    app = Flask(__name__)

    regiter_routes(app)

    return app