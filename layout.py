from dash import callback, Input, Output, html, dcc, clientside_callback, no_update
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from flask import g, abort
from layout_impl.header import header, header_init_targets
from layout_impl.left_sidebar import left_sidebar, left_sidebar_init_targets
from layout_impl.main_body import main_body, main_body_init_targets
from layout_impl.reusable import OnceInterval

from workflow.raw import clientside_collector as raw_clientside_collector
from workflow.epoch import clientside_collector as epoch_clientside_collector
from workflow.evoked import clientside_collector as evoked_clientside_collector
from workflow.esi import clientside_collector as esi_clientside_collector


def right_sidebar():
    return dbc.Col(id="right-sidebar", width=2, children=[
    
    ])

def footer():
    return dbc.Row(dbc.Col(id="footer", width=12, children="Foooter placeholder"))

def get_layout():
    # FIXME Actually, consider remove this
    # HACK In order to prevent Dash send a lot of useless data through internet, caused by generic callback with ALL
    # A clientside callback is used to collect change-related data and send them
    # Called "clientside collector" by me
    # This is very cursed
    clientside_collector = raw_clientside_collector + epoch_clientside_collector + evoked_clientside_collector + esi_clientside_collector
    for cc in clientside_collector:
        clientside_callback(cc[1], Output(cc[0], "data"), *cc[2:])
    
    return dmc.MantineProvider(
        children=(
            dcc.Location(id="redirect-location"),
            dmc.NotificationProvider(),
            html.Div(
                id="notifications-container",
            ),
            html.Div(
                id="main-container",
                children=( 
                    # HACK 为了保证初始化仅执行一次
                    OnceInterval(
                        id="usr-init-interval",
                    ),
                    
                    # 一个巨大的spinner，包裹着整个网页的内容
                    dcc.Loading(
                        id="whole-loading",
                        fullscreen=True,
                        display="show",
                        children=(
                            header(),
                            dbc.Row(
                                id="body",
                                children=(
                                    left_sidebar(),
                                    main_body(),
                                )
                            ),
                            # footer()
                        )
                    ),

                    # HACK This is even more cursed
                    *[
                        dcc.Store(
                            id=cc[0],
                            storage_type="memory",
                            clear_data=True
                        ) for cc in clientside_collector
                    ]
                )
            )
        )
    )

# HACK 用于初始化
# this is cursed
init_targets = header_init_targets + left_sidebar_init_targets + main_body_init_targets
@callback(
    *[Output(t[0], t[1]) for t in init_targets],
    Output("whole-loading", "display"),
    Input("usr-init-interval", "n_intervals"),
)
def init_user_data(_):
    # abort(401)
    if g.get("user_data") is not None:
        return *[t[2]() for t in init_targets], "hide"
    abort(401)