from flask import Flask, g, request, abort, redirect, render_template, jsonify
from dash import Dash, _dash_renderer
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from sys import argv
from db import db_util, memcached_util
from layout import get_layout
import dash_uploader as du
import json
import jwt
from auth import init_auth

server = Flask(__name__)
init_auth(server)

external_stylesheets = ["/static/style.css", dbc.themes.BOOTSTRAP, dmc.styles.NOTIFICATIONS]
_dash_renderer._set_react_version("18.2.0")
app = Dash(
    server=server, 
    external_stylesheets=external_stylesheets,
    title="GENII", 
    update_title=None
    # 这个参数抑制callback相关的exception
    # 比如，一开始在页面上不存在的，动态生成的按钮，它的callback会报错说元素不存在
    # 用这个参数可以抑制这类报错，但是也会抑制真正的错误（打错id之类的）
    # suppress_callback_exceptions=True
)

# 自定义的renderer，每次request前都手动放入Authorization header
# now use JWT, no longer needed
# app.renderer = '''
# var renderer = new DashRenderer({
#     request_pre: (payload) => {
#         // console.log(payload);
#         store.getState().config.fetch.headers['Authorization'] = atob(localStorage.getItem("auth-key"));
#         // store.getState().config.fetch.headers['Authorization'] = "asdasdasd"
#     },
#     request_post: (payload, response) => {
#         // console.log(payload);
#         // console.log(store.getState());
#     }
# })
# '''


du.configure_upload(app, "uploaded_files")
app.layout = get_layout()

if __name__ == '__main__':
    if argv[1:2] == ["prod"]:
        # TODO change to WSGI server for production https://community.plotly.com/t/how-to-add-your-dash-app-to-flask/51870/2
        # raise NotImplementedError("Production mode not implemented")
        # du.configure_upload(app, ???)
        app.run(debug=False, dev_tools_ui=False, dev_tools_props_check=False, port=8892)
    else:
        app.run(debug=True, port=8892)
        # app.run(debug=False, port=8892)

# from dash import Output, callback, Input, State
# import json

# @du.callback(
#     output=Output("test", "children"),
#     id="test-static-upload"
# )
# def test_static(filenames):
#     print("called static")
#     return json.dumps(filenames)

# @callback(
#     Output("test", "children"),
#     Input("default-upload", "isCompleted"),
#     State("default-upload", "fileNames"),
#     State("default-upload", "upload_id"),
#     prevent_initial_call=True
# )
# def test(a, b, c):
#     print("called")
#     return json.dumps([a, b, c, g.user_data])