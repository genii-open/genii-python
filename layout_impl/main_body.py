import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dcc, html, callback, Output, Input, State, ALL, ctx, no_update, MATCH, clientside_callback, Patch
from dash_iconify import DashIconify
from time import time
from layout_impl.reusable import FillOnHoverCloseTabBtn, OnceInterval
import dash_uploader as du
from flask import g

def main_body():
    return dbc.Col(
        id="content",
        className="position-relative h-100",
        width=10,
        children=(
            dbc.Container(
                id="content-container",
                className="h-100",
                children=render_default_tab(),
            ),

            # Callback is in left_sidebar.py
            html.Div(
                id="collapse-btn",
                className="bg-light",
                style={
                    "position": "absolute",
                    "left": "0",
                    "bottom": "0",
                    "padding": "5px",
                    "paddingLeft": "15px",
                    "height": "42px",
                    "borderRadius": "10px"
                },
                role="button",
                children=DashIconify(icon="material-symbols:chevron-left")
            ),
        )
    )

def render_default_tab():
    # FIXME The file upload provided by dash converts the entire file into base64
    # Very inefficient to handle large file
    # Currently using dash_uploader package, but:
    #   1. It bypass authentication
    #   2. Its callback never fire, probably because the component is dynamically generated

    # FIXME after cancel upload, temporary file will not be removed
    return dmc.Tabs(
        id="content-tabs",
        value="0",
        className="h-100",
        children=(
            dmc.TabsList(
                id="content-tab-list",
                children=( 
                    dmc.TabsTab(
                        id={"type": "content-tab-list", "index": "0"},
                        value="0",
                        children="Default",
                    ),
                )
            ),
            dmc.TabsPanel(
                id={"type": "content-tab-panel", "index": "0"},
                className="content-tab-panels",
                value="0",
                children=(
                    dbc.Container(
                        id="default-upload-container",
                        className="mt-3"
                    ),
                    html.Div(id="test")
                )
            ),
        )
    ),

# Require:
#       Output("content-tabs", "children", allow_duplicate=True),
#       Output("content-tabs", "value", allow_duplicate=True),
#       ...
#       State({"type": "content-tab-list", "index": ALL}, "value"),
#       prevent_initial_call=True
def append_to_tabs(tab_values, new_tab_title, new_tab_content):
    # Binary trick to find the smallest value not in the list
    # Assume all item in the list are >= 0 and will not repeat
    bit = 0
    index = 0
    for v in tab_values:
        bit += 1 << int(v)
    while bit % 2 != 0:
        bit >>= 1
        index += 1
    
    index = str(index)

    content_tabs = Patch()
    content_tabs[0]["props"]["children"].append(
        dmc.TabsTab(
            id={"type": "content-tab-list", "index": index},
            value=index,
            rightSection=FillOnHoverCloseTabBtn(
                id={"type": "content-tab-list-close-span", "index": index}
            ),
            # mod={"data-time": time()},
            children=new_tab_title
        )
    )

    content_tabs.append(
        dmc.TabsPanel(
            id={"type": "content-tab-panel", "index": index},
            className="content-tab-panels",
            value=index,
            children=new_tab_content
        )
    )

    return content_tabs, index

@callback(
    Output("content-tabs", "children", allow_duplicate=True),
    Output("content-tabs", "value", allow_duplicate=True),
    Input({"type": "content-tab-list-close-span", "index": ALL}, "n_clicks"),
    State({"type": "content-tab-list", "index": ALL}, "value"),
    State({"type": "content-tab-list", "index": ALL}, "mod"),
    prevent_initial_call=True
)
def close_tab(_, tab_values, interact_time):    
    # HACK Detecting triggered element of generic callback is confusing
    # Checking ctx.triggered_prop_id[str(ctx.triggered_id)+".n_clicks"] is None MIGHT work
    # But dict does not gaurantee the order of keys, hence does not gaurantee the output of str(dict)?
    # Here using the fact that it is a close button, hence can only clicked once per lifetime
    # Therefore checking the value of n_clicks will work
    if not any(_):
        return no_update

    for i in range(len(_)):
        if _[i] is not None and _[i] > 0:
            break

    tab_state = Patch()
    del tab_state[0]["props"]["children"][i + 1] # +1 for default tab title
    del tab_state[i + 2] # +1 for tablists, +1 for default tab
    del tab_values[i + 1]
    del interact_time[i + 1]

    last_interacted = 0
    for i in range(1, len(interact_time)):
        if interact_time[i]["data-time"] > interact_time[last_interacted]["data-time"]:
            last_interacted = i

    return tab_state, tab_values[last_interacted]
    #TODO test

    # if isinstance(tab_state, list):
    #     tab_state = tab_state[0]

    # for s in tab_state["props"]["children"]:
    #     if s["type"] == "TabsList":
    #         if len(s["props"]["children"]) == 1:
    #             return render_default_tab()
    #         tabs_list_state = s
    #         break
    # tabs_panel_state = [s for s in tab_state["props"]["children"] if s["type"] != "TabsList"]
    
    # tab_state["props"].pop("value", None)
    # tab_state["props"].pop("children")

    # tabs_list_state["props"]["children"] = [
    #     c for c in tabs_list_state["props"]["children"] if c["props"]["id"]["index"] != ctx.triggered_id["index"]
    # ]
    
    # tabs_panel_state = [
    #     p for p in tabs_panel_state if p["props"]["id"]["index"] != ctx.triggered_id["index"]
    # ]

    # # Get the newest tab/recently interacted tab
    # new_tab_time = tabs_list_state["props"]["children"][0]["props"]["mod"]["data-time"]
    # new_tab_value = tabs_list_state["props"]["children"][0]["props"]["value"] 
    # for t in tabs_list_state["props"]["children"][1:]:
    #     if new_tab_time < t["props"]["mod"]["data-time"]:
    #         new_tab_time = t["props"]["mod"]["data-time"]
    #         new_tab_value = t["props"]["value"]

    # return dmc.Tabs(
    #     value=new_tab_value,
    #     # value=tabs_list_state["props"]["children"][0]["props"]["value"],
    #     children=(
    #         tabs_list_state,
    #         *tabs_panel_state
    #     ),
    #     **tab_state["props"]
    # )


# HACK keep track of the timestamp of last interaction for each tab
# So that when a tab is closed, the newest one will be focused on 
# This approach is like caveman
# TODO use clientside_callback for efficiency, move into the rendering function above
# clientside_callback(
#     """
#     () => 
#     """,
#     Output({"type": "content-tab-list", "index": ALL}, "mod"),
#     Input("content-tabs", "value"),
#     State({"type": "content-tab-list", "index": ALL}, "value")
# )

@callback(
    Output({"type": "content-tab-list", "index": ALL}, "mod"),
    Input("content-tabs", "value"),
    State({"type": "content-tab-list", "index": ALL}, "value")
)
def update_interacted_time(value, values):
    # print(values)
    if value not in values:
        return no_update
    out = [no_update for _ in values]
    out[values.index(value)] = {"data-time": time()}
    return out

def make_upload():
    return du.Upload(
        id="default-upload",
        upload_id=str(g.user_data["id"])
    )

main_body_init_targets = (
    ("default-upload-container", "children", make_upload),
)