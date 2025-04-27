from flask import g
from dash import html, clientside_callback, Output, Input, callback, no_update
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
from auth import logout_user, _LOGIN_URL

def header():
    # clientside_callback(
    #     """
    #     (_) => {
    #         if (_) {
    #             window.localStorage.removeItem("auth-key");
    #             return "/login"
    #         }
    #         return dash_clientside.no_update;
    #     }
    #     """,
    #     Output("redirect-location", "href"),
    #     Input("header-logout", "n_clicks")
    # )
    return dbc.Row(
        id="header",
        className=("bg-dark"),
        children=(
            dbc.Col(
                width=9,
                className="d-flex align-items-center",
                children=(
                    html.Img(
                        id="logo",
                        src="static/logo.png"
                    ),
                    html.Div(
                        className="d-flex flex-column mt-2",
                        children=(
                            html.H1(
                                children="GENII",
                                style={
                                    "fontFamily": "Times New Roman",
                                    "color": "white",
                                    "marginBottom": "0",
                                    "lineHeight": "1"
                                }
                            ),
                            html.Pre(
                                children="General Electrophysiological Neuro-Interface and Intelligence",
                                style={
                                    "fontFamily": "Times New Roman",
                                    "color": "white",
                                    "fontSize": "5",
                                    "lineHeight": "1",
                                    "overflow": "visible"
                                }
                            ),
                        )
                    ),
                )
            ),
            dbc.Col(
                width=2,
                className="d-flex align-items-center",
                children=html.P(
                    id="usrname",
                    style={"color": "white"}
                )
            ),
            dbc.Col(
                width=1,
                className="d-flex align-items-center",
                children=(
                    html.Span(
                        id="header-logout",
                        role="button",
                        children=DashIconify(icon="material-symbols:logout-sharp", color="white", width=30)
                    )
                )
            )
        )
    )

def init_usrname():
    return "Welcome, " + g.user_data["name"]


header_init_targets = (
    ("usrname", "children", init_usrname),
)

@callback(
    Output("redirect-location", "href"),
    Input("header-logout", "n_clicks"),
    prevent_initial_call=True
)
def logout(_):
    if _ == 0: return no_update
    return logout_user()