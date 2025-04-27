from flask import Flask, request, g, render_template, jsonify, redirect, abort, Response
import json
from db import db_util, memcached_util
import jwt
import uuid
from datetime import datetime, timezone, timedelta
from db.data_structure import UserData, File
from typing import Tuple

def init_auth(server: Flask) -> Flask:
    server.before_request(_authCookie)
    server.errorhandler(401)(_handle_unauthorized)

    server.route(_LOGIN_URL, methods=["GET"])(_render_login)
    server.route(_LOGIN_API, methods=["POST"])(_handle_login)

    return server

def get_user_data() -> UserData:
    return g.user_data

def get_cached_file() -> Tuple[File, ...]:
    return g.cached_files

def logout_user():
    # TODO delete JWT at clientside
    user_data = get_user_data()
    db_util.user_logout(user_data.id)
    return _LOGIN_URL

_JWT_COOKIE_NAME = "XMUMMC_NEUROII"
_JWT_SECRET_KEY = "GENII_CMMUMX"
_JWT_ALGORITHM = "HS256"
_JWT_LIFE = timedelta(days=7)
_JWT_TOKEN_KEY = "token"

_LOGIN_URL = "/login"
_LOGIN_API = "/api/auth/login"
_WHITE_LIST_URL = [_LOGIN_URL, _LOGIN_API]

# Hand-crafted response to trigger redirection to the login page
# https://community.plotly.com/t/how-to-handle-with-redirect-in-dash-app/81839/7    
_UNAUTHORIZED_DASH = json.dumps({  
    "multi": True,  
    "response": {  
        "redirect-location": {
            "href": _LOGIN_URL,
        }
    }  
})
_UNAUTHORIZED_GENERAL = redirect(_LOGIN_URL)

def _authCookie():
    if request.path[:7] == "/static": return None
    if request.path in _WHITE_LIST_URL: return None
    
    cookie = request.cookies.get(_JWT_COOKIE_NAME)
    if not cookie:
        abort(401)
        # return _UNAUTHORIZED_GENERAL
    
    try:
        token = jwt.decode(cookie, _JWT_SECRET_KEY, algorithms=[_JWT_ALGORITHM])[_JWT_TOKEN_KEY]
    # except (jwt.InvalidIssuedAtError, jwt.ExpiredSignatureError, jwt.InvalidTokenError):
    except:
        abort(401)
        # return _UNAUTHORIZED_GENERAL

    user_data = db_util.get_user_detail_wih_token(token)
    if user_data is None:
        abort(401)
        # return _UNAUTHORIZED_GENERAL
    g.user_data = user_data
    g.cached_files = memcached_util.get_cached_files(token)
    

    # if request.path == '/_dash-update-component' and request.method == 'POST':   
    #     if not request.headers.get("Authorization"):
    #         return _UNAUTHORIZED
    #     g.user_data = db_util.get_user_detail_wih_token(request.headers.get("Authorization"))
    #     if g.user_data is None:
    #         return _UNAUTHORIZED
    #     g.cached_files = memcached_util.get_cached_files(request.headers.get("Authorization"))

def _handle_unauthorized(_):
    if request.path == '/_dash-update-component' and request.method == 'POST':   
        return _UNAUTHORIZED_DASH
    return _UNAUTHORIZED_GENERAL

def _render_login():
    return render_template("login.html")

def _handle_login():
    token = db_util.user_login(request.form["email"], request.form["pwd"])
    if token is None:
        return jsonify({"success": False})
    res = jsonify({"success": True})
    cookie = jwt.encode({
            _JWT_TOKEN_KEY: str(token),
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + _JWT_LIFE
        }
        , _JWT_SECRET_KEY, algorithm=_JWT_ALGORITHM)
    res.set_cookie(
        _JWT_COOKIE_NAME, cookie, httponly=True, secure=True,
        max_age=_JWT_LIFE, samesite="Lax"
    )
    return res

# class CustomHttpRequestHandler(du.HttpRequestHandler):

#     def validate_cookie(self):
#         token = request.cookies.get(_JWT_COOKIE_NAME)
#         return token and verify_cookie(token)

#     def post_before(self):
#         if not self.validate_cookie():
#             self.abort_upload()

#     def get_before(self):
#         if not self.validate_cookie():
#             self.abort_upload()

#     def abort_upload(self):
#         from flask import jsonify, abort
#         # response = jsonify({"status": "error", "message": "Unauthorized: Cookie invalid or expired."})
#         # abort(response, 401)
#         abort(401)

# Cookie generation callback
# @app.callback(
#     Output("cookie-status", "children"),
#     Output("cookie-present", "data"),
#     Input("generate-cookie", "n_clicks"),
#     State("expiration-input", "value"),
#     prevent_initial_call=True
# )
# def generate_cookie_callback(n_clicks, expiration_minutes):
#     expiration_minutes = max(expiration_minutes, 0)
#     cookie_value = generate_cookie_value(expiration_minutes)
#     callback_context.response.set_cookie(
#         _JWT_COOKIE_NAME, cookie_value, httponly=True, secure=False,
#         max_age=expiration_minutes * 60
#     )
#     expiration_text = f"{expiration_minutes} minute{'s' if expiration_minutes != 1 else ''}"
#     return (f"Authentication cookie generated! Expires in {expiration_text}.", True)
