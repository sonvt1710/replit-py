"""A module containing a database proxy implementation."""

from typing import Any
from urllib.parse import quote

from flask import Blueprint, Flask, request

from . import default_db


def make_database_proxy_blueprint(view_only: bool, prefix: str = "") -> Blueprint:
    """Generates a blueprint for a database proxy.

    Args:
        view_only: If False, database writing and deletion is enabled.
        prefix: A prefix that all keys interacted with using this proxy will use.

    Returns:
        Blueprint: A flask blueprint with the proxy logic.
    """
    app = Blueprint("database_proxy" + ("_view_only" if view_only else ""), __name__)

    def list_keys() -> Any:
        if default_db.db is None:
            return "Database is not configured", 500
        user_prefix = request.args.get("prefix", "")
        encode = "encode" in request.args
        raw_keys = default_db.db.prefix(prefix=prefix + user_prefix)
        keys = [k[len(prefix) :] for k in raw_keys]

        if encode:
            return "\n".join(quote(k) for k in keys)
        else:
            return "\n".join(keys)

    def set_key() -> Any:
        if default_db.db is None:
            return "Database is not configured", 500
        if view_only:
            return "Database is view only", 401
        for k, v in request.form.items():
            default_db.db[prefix + k] = v
        return ""

    @app.route("/", methods=["GET", "POST"])
    def index() -> Any:
        if request.method == "GET":
            return list_keys()
        return set_key()

    def get_key(key: str) -> Any:
        if default_db.db is None:
            return "Database is not configured", 500
        try:
            return default_db.db[prefix + key]
        except KeyError:
            return "", 404

    def delete_key(key: str) -> Any:
        if default_db.db is None:
            return "Database is not configured", 500
        if view_only:
            return "Database is view only", 401
        try:
            del default_db.db[prefix + key]
        except KeyError:
            return "", 404
        return ""

    @app.route("/<key>", methods=["GET", "DELETE"])
    def manage_key(key: str) -> Any:
        if request.method == "GET":
            return get_key(key)
        return delete_key(key)

    return app


def start_database_proxy(
    view_only: bool,
    prefix: str = "",
    host: str = "0.0.0.0",  # noqa: S104
    port: int = 8080,
) -> None:
    """Starts the database proxy."""
    app = Flask(__name__)

    app.register_blueprint(make_database_proxy_blueprint(view_only, prefix=prefix))
    app.run(host=host, port=port)
