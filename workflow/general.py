from dash import dcc, html, callback, Input, Output, State, ALL, MATCH, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
from path_based_id_util import make_id, make_generic_id, decode_path
from db.data_structure import File, FileType
from file_io import cache_file, read_check_and_cache_file, validate_access, save_mne_object, get_appropriate_ext
from db.memcached_util import remove_cache
import os
import mne
from flask import g
import traceback

# FIXME this thing is potentially very broken

def render_general_function(file: File):
    ch_order = file.item.info["ch_names"]
    return dbc.Container(
        # id=make_id(file.path, type="general-function-container"),
        style={"height": "30vh"},
        children=(
            dmc.Tabs(
                value="filter",
                children=(
                    dmc.TabsList(
                        grow=True,
                        children=(
                            dmc.TabsTab(
                                # id=make_id(file.path, type="general-function-tab-list", index="filter"),
                                value="file-op",
                                children=DashIconify(icon="tabler:file"),
                            ),
                            dmc.TabsTab(
                                # id=make_id(file.path, type="general-function-tab-list", index="filter"),
                                value="filter",
                                children=DashIconify(icon="tabler:filter"),
                            ),
                            dmc.TabsTab(
                                # id=make_id(file.path, type="general-function-tab-list", index="ch_order"),
                                value="ch_order",
                                children=DashIconify(icon="lets-icons:sort-list-light"),
                            ),
                            dmc.TabsTab(
                                # id=make_id(file.path, type="general-function-tab-list", index="reference"),
                                value="reference",
                                children=DashIconify(icon="tabler:topology-ring"),
                            ),
                        )
                    ),
                    dmc.TabsPanel(
                        # id=make_id(file.path, type="general-function-tab-panel", index="ch_order"),
                        value="file-op",
                        children=(
                            dbc.InputGroup(
                                children=(
                                    dbc.Button(
                                        id=make_id(file.path, type="file-op-save-as-btn"),
                                        title="Save As",
                                        children=DashIconify(icon="mdi:content-save-plus-outline")
                                    ),
                                    dbc.Input(
                                        id=make_id(file.path, type="file-op-save-as-name-input"),
                                    ),
                                )
                            ),

                        )
                    ),
                    dmc.TabsPanel(
                        # id=make_id(file.path, type="general-function-tab-panel", index="filter"),
                        value="filter",
                        children=(
                            html.P(children="Bandpass filter:"),
                            dbc.InputGroup(
                                children=(
                                    dbc.Input(
                                        id=make_id(file.path, type="general-highpass"),
                                        value=file.item.info["highpass"],
                                        type="number"
                                    ),
                                    dbc.InputGroupText("~"),
                                    dbc.Input(
                                        id=make_id(file.path, type="general-lowpass"),
                                        value=file.item.info["lowpass"],
                                        type="number"
                                    )
                                )
                            ),
                            dbc.Button(
                                id=make_id(file.path, type="general-perform-filter"),
                                children="Filter"
                            )
                        )
                    ),
                    dmc.TabsPanel(
                        # id=make_id(file.path, type="general-function-tab-panel", index="ch_order"),
                        value="ch_order",
                        children=ch_order
                    ),
                    dmc.TabsPanel(
                        # id=make_id(file.path, type="general-function-tab-panel", index="reference"),
                        value="reference",
                        children=(
                            dmc.Switch(
                                id=make_id(file.path, type="general-use-bipolar"),
                                checked=False,
                                label="Use bipolar reference",
                                size="lg"
                            ),
                        )
                    ),
                )
            ),
        )
    )

# HACK reset supposed "once" interval to trigger rerendering of graph
@callback(
    Output(make_generic_id(MATCH, type="raw-once-interval"), "n_intervals", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="general-perform-filter"), "n_clicks"),
    State(make_generic_id(MATCH, type="general-highpass"), "value"),
    State(make_generic_id(MATCH, type="general-lowpass"), "value"),
    State(make_generic_id(MATCH, type="general-perform-filter"), "id"),
    prevent_initial_call=True,
    running=(
        (Output(make_generic_id(MATCH, type="raw-graph-loading"), "display"), "show", "hide"),
    )
)
def raw_perform_filter(_, highpass, lowpass, id):
    if ctx.triggered_id is None:
        return no_update
    file = read_check_and_cache_file(decode_path(id))
    return _alter_view(file, highpass=highpass, lowpass=lowpass)

@callback(
    Output(make_generic_id(MATCH, type="epoch-once-interval"), "n_intervals", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="general-perform-filter"), "n_clicks"),
    State(make_generic_id(MATCH, type="general-highpass"), "value"),
    State(make_generic_id(MATCH, type="general-lowpass"), "value"),
    State(make_generic_id(MATCH, type="general-perform-filter"), "id"),
    prevent_initial_call=True,
    running=(
        (Output(make_generic_id(MATCH, type="epoch-graph-loading"), "display"), "show", "hide"),
    )
)
def epoch_perform_filter(_, highpass, lowpass, id):
    if ctx.triggered_id is None:
        return no_update
    file = read_check_and_cache_file(decode_path(id))
    return _alter_view(file, highpass=highpass, lowpass=lowpass)

@callback(
    Output(make_generic_id(MATCH, type="evoked-once-interval"), "n_intervals", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="general-perform-filter"), "n_clicks"),
    State(make_generic_id(MATCH, type="general-highpass"), "value"),
    State(make_generic_id(MATCH, type="general-lowpass"), "value"),
    State(make_generic_id(MATCH, type="general-perform-filter"), "id"),
    prevent_initial_call=True,
    running=(
        (Output(make_generic_id(MATCH, type="evoked-ch-graph-loading"), "display"), "show", "hide"),
    )
)
def evoked_perform_filter(_, highpass, lowpass, id):
    if ctx.triggered_id is None:
        return no_update
    file = read_check_and_cache_file(decode_path(id))
    return _alter_view(file, highpass=highpass, lowpass=lowpass)


@callback(
    Output(make_generic_id(MATCH, type="raw-once-interval"), "n_intervals", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="general-use-bipolar"), "checked"),
    State(make_generic_id(MATCH, type="general-use-bipolar"), "id"),
    prevent_initial_call=True,
    running=(
        (Output(make_generic_id(MATCH, type="raw-graph-loading"), "display"), "show", "hide"),
    )
)
def raw_switch_reference(checked, id):
    if ctx.triggered_id is None:
        return no_update
    file = read_check_and_cache_file(decode_path(id))
    return _alter_view(file, use_bipolar=checked)

@callback(
    Output(make_generic_id(MATCH, type="epoch-once-interval"), "n_intervals", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="general-use-bipolar"), "checked"),
    State(make_generic_id(MATCH, type="general-use-bipolar"), "id"),
    prevent_initial_call=True,
    running=(
        (Output(make_generic_id(MATCH, type="epoch-graph-loading"), "display"), "show", "hide"),
    )
)
def epoch_switch_reference(checked, id):
    if ctx.triggered_id is None:
        return no_update
    file = read_check_and_cache_file(decode_path(id))
    return _alter_view(file, use_bipolar=checked)

@callback(
    Output(make_generic_id(MATCH, type="evoked-once-interval"), "n_intervals", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="general-use-bipolar"), "checked"),
    State(make_generic_id(MATCH, type="general-use-bipolar"), "id"),
    prevent_initial_call=True,
    running=(
        (Output(make_generic_id(MATCH, type="evoked-ch-graph-loading"), "display"), "show", "hide"),
    )
)
def evoked_switch_reference(checked, id):
    if ctx.triggered_id is None:
        return no_update
    file = read_check_and_cache_file(decode_path(id))
    return _alter_view(file, use_bipolar=checked)




def _alter_view(file: File, **kwargs):
    reachable, todo = _state_reachable(file.item, **kwargs)
    
    if not reachable:
        remove_cache(file.path)
        file = read_check_and_cache_file(file.path)
    
    item = file.item
    if "use_bipolar" in todo and todo["use_bipolar"]:
        item = _use_bipolar(item)
    if "highpass" in todo or "lowpass" in todo:
        item = _filter(item, todo["highpass"], todo["lowpass"])
    state = {
        "use_bipolar": False,
        "highpass": file.item.info["highpass"],
        "lowpass": file.item.info["lowpass"]
    } if not reachable else file.item.info["temp"]["state"]
    state.update(todo)
    file.item.info["temp"] = {
        "state": state
    }
    print(file.item.info["temp"]["state"])
    cache_file(file.item, file.item_type, True, file.path)
    return 0

def _state_reachable(item, **kwargs):
    if item.info.get("temp", None) is None:
        return False, kwargs
    else:
        state = item.info["temp"]["state"]
        # bipolar -> average
        if "use_bipolar" in kwargs and state["use_bipolar"] and not kwargs["use_bipolar"]:
            state.update(kwargs)
            return False, state
        # lost info about freq < highpass
        elif "highpass" in kwargs and state["highpass"] < kwargs["highpass"]:
            state.update(kwargs)
            return False, state
        # lost info about freq > lowpass
        elif "lowpass" in kwargs and state["lowpass"] > kwargs["lowpass"]:
            state.update(kwargs)
            return False, state
    return True, kwargs

def _filter(item, highpass, lowpass):
    if highpass <= item.info["highpass"]:
        highpass = None
    if lowpass >= item.info["lowpass"]:
        lowpass = None
    
    return item.filter(highpass, lowpass)

def _use_bipolar(item):
    return mne.set_bipolar_reference(
        item,
        anode=[ "Fp2", "F8", "T4", "T6", "Fp2", "F4", "C4", "P4", "Fz", "Cz", "Fp2", "F3", "C3", "P3", "Fp1", "F7", "T3", "T5" ],
        cathode=[ "F8",  "T4", "T6", "O2", "F4",  "C4", "P4", "O2", "Cz", "Pz", "F3",  "C3", "P3", "O1", "F7",  "T3", "T5", "O1" ]
    )

@callback(
    Output("notifications-container", "children", allow_duplicate=True),
    Input(make_generic_id(ALL, type="file-op-save-as-btn"), "n_clicks"),
    State(make_generic_id(ALL, type="file-op-save-as-name-input"), "value"),
    State(make_generic_id(ALL, type="file-op-save-as-name-input"), "id"),
    prevent_initial_call=True
)
def save_file_as(_, name, id):
    # print("delete")
    if len(_) == 0: return no_update
    if not any(_): return no_update

    # NOTE if exception occur, and notification is one of the Output, previous notification will be replayed
    try:
        path = decode_path(ctx.triggered_id)
        name_idx = [decode_path(i) for i in id].index(path)
        save_as_path = os.path.join(g.user_data["wd"], name[name_idx])
        # validate_access(path)
        # print("delete")
        # print(path)
        file = read_check_and_cache_file(path)
        save_mne_object(file.item.copy(), save_as_path + get_appropriate_ext(file.item_type))
        
        notif = dmc.Notification(
            title="File Saved!",
            action="show",
            message=f"{name[name_idx]} saved",
            icon=DashIconify(icon="ep:success-filled", color="chartreuse", width=30)
        )
    except:
        print(traceback.format_exc())
        notif = dmc.Notification(
            title="Failed to save file",
            action="show",
            message=f"Failed to save file {path[len(g.user_data['wd']) +  1:]}",
            icon=DashIconify(icon="ep:circle-close-filled", color="red", width=30)
        )
    return notif
