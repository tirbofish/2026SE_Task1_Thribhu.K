from flask import Flask
from .auth import __register_routes as auth_register
from .devlog import __register_routes as devlog_register

def register_routes(app: Flask):
    """Registers all routes and endpoints in the devlog app

    Args:
        app (Flask): The Flask app that this will be registered to. 
    """
    auth_register(app)
    devlog_register(app)