import mne
import dash_bootstrap_components as dbc
from .util import plot_to_base64
from dash import html, callback, Input, Output, State, ctx, no_update, dcc, MATCH, ALL
from file_io import read_and_cache_file, cache_file
from db.data_structure import FileType, File
import os
from layout_impl.main_body import append_to_tabs
from workflow.evoked import render_evoked_content
from path_based_id_util import make_id, make_generic_id, decode_path
from layout_impl.reusable import OnceInterval
from dash_iconify import DashIconify
import numpy as np
from plotly.graph_objs import Layout, Scatter, Figure
from plotly.graph_objs.layout import YAxis, Annotation, Font, shape

from .plotting_util import decide_ch_color
from .general import render_general_function

from datetime import datetime

_PAGE_LEN = 5

clientside_collector = (
    (
        "compute-evoked-info-collector",
        # FIXME Use ClientsideFunction for sanity
        # NOTE used magic key pth and ext
        # NOTE only 1 trigger allowed
        """
        (i,m)=>{
            console.log("EPOCH CC");
            console.log(dash_clientside.callback_context);
            console.log({i, m});
            
            // Check initial call
            if (
                dash_clientside.callback_context.triggered.length === 0 ||
                !dash_clientside.callback_context.triggered[0].value
            ){
                console.log("Initial call: no update");
                return dash_clientside.no_update;
            }
            triggered_id = JSON.parse(
                dash_clientside.callback_context.triggered[0].prop_id.split(".")[0]
            );
            triggered_id.type = undefined;
            triggered_id.n_clicks = dash_clientside.callback_context.inputs_list
                .find(
                    s => s[0].id.ext === triggered_id.ext && s[0].id.pth === triggered_id.pth
                )[0].value;
            console.log(triggered_id);
            // Check call due to recreation of tabs
            if ((m && Object.entries(triggered_id).every((kv) => m[kv[0]] === kv[1]))){
                console.log("Repeated call: no update")
                return dash_clientside.no_update;
            }
            return triggered_id;
        }
        """,
        Input(make_generic_id(ALL, type="compute-evoked-btn"), "n_clicks"),
        State("compute-evoked-info-collector", "data"),
    ),
)

def render_epoch_content(file: File):
    title = "Epoch: " + os.path.basename(file.path)
    if file.dirty:
        title = "*" + title
    content = dbc.Row(
        className="max-h-100",
        children=(
            dbc.Col(
                # id=make_id(file.path, "epoch-main-content"),
                width=9,
                children=(
                    dcc.Loading(
                        id=make_id(file.path, type="epoch-graph-loading"),
                        className="h-100",
                        display="show",
                        children=(
                            dcc.Graph(
                                id=make_id(file.path, type="epoch-graph"),
                            ),
                            dbc.InputGroup(
                                # id=make_id(file.path, type="epoch-graph-control"),
                                children=(
                                    dbc.Button(
                                        id=make_id(file.path, type="epoch-graph-back-start"),
                                        children=DashIconify(icon="gg:play-backwards"),
                                        title="Move to the start of file"
                                    ),
                                    dbc.Button(
                                        id=make_id(file.path, type="epoch-graph-back-page"),
                                        children=DashIconify(icon="gg:play-track-prev"),
                                        title="Move back by 1 epoch"
                                    ),
                                    dbc.InputGroupText("Show"),
                                    dbc.Input(
                                        id=make_id(file.path, type="epoch-graph-page-len"),
                                        type="number",
                                        value=_PAGE_LEN,
                                        min=1,
                                        step=1
                                    ),
                                    dbc.InputGroupText("epoch(s)"),
                                    dbc.Button(
                                        id=make_id(file.path, type="epoch-graph-fwd-page"),
                                        children=DashIconify(icon="gg:play-track-next"),
                                        title="Move forward by 1 epoch"
                                    ),
                                    dbc.Button(
                                        id=make_id(file.path, type="epoch-graph-fwd-end"),
                                        children=DashIconify(icon="gg:play-forwards"),
                                        title="Move to the start of file"
                                    ),
                                    dcc.Store(
                                        id=make_id(file.path, type="epoch-graph-start-idx"),
                                        clear_data=True,
                                        data=0
                                    )
                                )
                            )
                        )
                    )
                ),
            ),
            dbc.Col(
                className="d-flex flex-column",
                width=3,
                children=(
                    render_general_function(file),
                    html.Div(
                        children=(
                            html.Table(
                                children=html.Tbody(
                                    id=make_id(file.path, type="epoch-ev-count-table"),
                                    children=(
                                        html.Tr(
                                            children=(
                                                html.Th("Time"),
                                                html.Td(f"{file.item.tmin: .2f}s ~ {file.item.tmax: .2f}s",)
                                            )
                                        ),
                                        *make_epoch_ev_count(file.item)
                                    )
                                )
                            )
                        )
                    ),
                    dcc.Dropdown(
                        id=make_id(file.path, type="drop-epochs-dropdown"),
                        multi=True,
                        clearable=True,
                        options=make_epoch_dropdown_options(file.item),
                        value=None
                    ),
                    dbc.Button(
                        id=make_id(file.path, type="drop-epochs-btn"),
                        children="Drop Epochs..."
                    ),
                    dbc.Button(
                        id=make_id(file.path, type="compute-evoked-btn"),
                        children="Compute Evoked Response..."
                    ),
                )
            ),
            OnceInterval(id=make_id(file.path, type="epoch-once-interval"))
        )
    )
    return title, content

# TODO these 2 funcs can be merged
def make_epoch_dropdown_options(epoch):
    ls = []
    for i, anns in enumerate(epoch.get_annotations_per_epoch()):
        min_i = 0
        min_diff = abs(anns[0][0])
        for ev_i, ev in enumerate(anns[1:]):
            if abs(ev[0]) < min_diff:
                min_i = ev_i
        ls.append({"label": f"{i + 1}: {anns[min_i][2]}", "value": i} )
    return ls

def make_epoch_ev_count(epoch):
    counts = {}
    for anns in epoch.get_annotations_per_epoch():
        min_i = 0
        min_diff = abs(anns[0][0])
        for ev_i, ev in enumerate(anns[1:]):
            if abs(ev[0]) < min_diff:
                min_i = ev_i
        counts[anns[min_i][2]] = counts.get(anns[min_i][2], 0) + 1
    return [
        html.Tr(
            children=(
                html.Th(k),
                html.Td(v)
            )
        ) for k, v in counts.items()
    ]


@callback(
    Output(make_generic_id(MATCH, type="epoch-graph"), "figure"),
    Output(make_generic_id(MATCH, type="epoch-graph-loading"), "display"),
    Input(make_generic_id(MATCH, type="epoch-once-interval"), "n_intervals"),
    Input(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data"),
    Input(make_generic_id(MATCH, type="epoch-graph-page-len"), "value"),
    State(make_generic_id(MATCH, type="epoch-once-interval"), "id"),
)
def render_epoch_graph(_, start_idx, page_len, id):
    if start_idx is None:
        start_idx = 0
    if page_len is None:
        page_len = _PAGE_LEN
    path = decode_path(id)
    epoch = read_and_cache_file(path)
    page_len = min(int(page_len), len(epoch))
    end_idx = start_idx + page_len
    # print(len(epoch))
    # print(len(epoch.times))
    # print(epoch.tmax - epoch.tmin)
    view = epoch
    # view = epoch.info.get("temp", {}).get("view", None)
    if view is None:
        data = epoch.get_data(copy=True)[start_idx:end_idx]
    else:
        # print(filt)
        data = view.get_data(copy=True)[start_idx:end_idx]
    concatenated_data = np.concatenate([d for d in data], axis=1)
    # print(concatenated_data.shape)

    #TODO mostly copied from raw render plot, can be pulled out to be a util function 
    step = 1. / epoch.info["nchan"]
    kwargs = dict(domain=[1 - step, 1], showticklabels=False, zeroline=False, showgrid=False, visible=False)

    # FIXME ???
    times = np.arange(0, concatenated_data.shape[1])

    # create objects for layout and traces
    # FIXME unable to show time at the bottom
    layout = Layout(
        xaxis=dict(showticklabels=False, zeroline=False, showgrid=False),
        yaxis=YAxis(kwargs), showlegend=False
    )
    traces = [Scatter(
        x=times,
        y=concatenated_data.T[:, 0],
        line={
            "color": decide_ch_color(epoch.info["ch_names"][0], epoch.info["bads"]),
            "width": 1
        }
    )]

    # loop over the channels
    for ii in range(1, epoch.info["nchan"]):
            kwargs.update(domain=[1 - (ii + 1) * step, 1 - ii * step])
            layout.update({'yaxis%d' % (ii + 1): YAxis(kwargs), 'showlegend': False})
            traces.append(Scatter(
                x=times,
                y=concatenated_data.T[:, ii],
                yaxis='y%d' % (ii + 1),
                line={
                    "color": decide_ch_color(epoch.info["ch_names"][ii], epoch.info["bads"]),
                    "width": 1
                }
            ))

    # add channel names using Annotations
    annotations = [
        Annotation(
            x=-0.06, y=0, xref='paper', yref='y%d' % (ii + 1),
            text=ch_name,
            showarrow=False
        ) for ii, ch_name in enumerate(epoch.info["ch_names"])
    ]

    layout.update(annotations=annotations, margin=dict(l=60, r=20, t=20, b=20),)
    fig = Figure(data=traces, layout=layout)
    
    ### End of copied code
    # Draw event line
    for i, ev in enumerate(epoch.get_annotations_per_epoch()[start_idx:end_idx]):
        for j in range(len(ev)):
            offset = i * len(epoch.times) + epoch.time_as_index(ev[j][0]).item()
            #FIXME? potential off by 1
            fig.add_shape(
                line=shape.Line(
                    dash="dot",
                    color="green",
                    width=1
                ),
                layer="between",
                x0=offset,
                y0=0,
                x1=offset,# TODO consider duration,
                y1=1,
                yref="paper",
                label=shape.Label(
                    text=ev[j][2],
                    textposition="top center"
                )
            )
    
    # Draw line that separate different epochs
    for i in range(end_idx - start_idx):
        x = len(epoch.times) * i + 1
        fig.add_shape(
            line=shape.Line(
                color="green",
                width=3 if i != 0 else 0
            ),
            layer="between",
            x0=x,
            y0=0,
            x1=x,
            y1=1,
            yref="paper",
            label=shape.Label(
                text=i + 1,
                textposition="bottom left"
            )
        )

    return fig, "hide"

@callback(
    Output("content-tabs", "children", allow_duplicate=True),
    Output("content-tabs", "value", allow_duplicate=True),
    Input("compute-evoked-info-collector", "data"),
    State({"type": "content-tab-list", "index": ALL}, "value"),
    prevent_initial_call=True
)
def compute_evoked(info, tab_values):
    # print(info)
    if info is None:
        return no_update
    path = decode_path(info)
    ep = read_and_cache_file(path)
    ev = ep.average()
    # if "temp" in ev.info:
    #     del ev.info["temp"]
    save_path = os.path.join(os.path.dirname(path), os.path.basename(path).split(".")[0])[:-4]
    # path = save_path + "-" + datetime.now().strftime("%d_%m_%y__%H_%M_%S") + "-ave.fif"
    path = save_path + "-ave.fif"
    ev.save(path, overwrite=True)
    ev = cache_file(ev, FileType.EVOKED, True, path)

    # path = save_path + ??? + "-ave.fif"
    # path = save_path + "-ave-epo.fif"
    # ep.save(path, overwrite=True)
    # cache_file(ep, FileType.EPOCH, True, save_path + "-" + datetime.now().strftime("%d_%m_%y__%H_%M_%S") + "-ave-epo.fif")
    return append_to_tabs(tab_values, *render_evoked_content(ev))

# Indirectly trigger rerender of epoch using render_epoch_graph() by changing the Inputs of it
@callback(
    Output(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data"),
    Output(make_generic_id(MATCH, type="drop-epochs-dropdown"), "value"),
    Output(make_generic_id(MATCH, type="drop-epochs-dropdown"), "options"),
    Output(make_generic_id(MATCH, type="epoch-ev-count-table"), "children"),
    Input(make_generic_id(MATCH, type="drop-epochs-btn"), "n_clicks"),
    State(make_generic_id(MATCH, type="drop-epochs-dropdown"), "value"),
    prevent_initial_callback=True,
)
def drop_epochs_with_index(_, epoch_idxs):
    if _ is None or ctx.triggered_id is None:
        return no_update
    
    path = decode_path(ctx.triggered_id)
    ep: mne.Epochs = read_and_cache_file(path)
    ep.drop(epoch_idxs)
    cache_file(ep, FileType.EPOCH, True, path)
    return 0, [], make_epoch_dropdown_options(ep), make_epoch_ev_count(ep)


#TODO copied from raw, probably can be merged into a generic control.py or something

# TODO stuff like this should be clientside callback but I am lazy
# This implementation cause 2 round trips for 1 graph update
@callback(
    Output(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="epoch-graph-back-start"), "n_clicks"),
    prevent_initial_call=True
)
def graph_control_back_to_start(_):
    return 0

@callback(
    Output(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="epoch-graph-back-page"), "n_clicks"),
    State(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data"),
    prevent_initial_call=True
)
def graph_control_back_one_ep(_, start_idx):
    if start_idx is None or start_idx < 0:
        start_idx = 0
    return max(start_idx - 1, 0)

@callback(
    Output(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="epoch-graph-fwd-page"), "n_clicks"),
    State(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data"),
    State(make_generic_id(MATCH, type="epoch-graph-page-len"), "value"),
    prevent_initial_call=True
)
def graph_control_fwd_one_ep(_, start_idx, page_len):
    if start_idx is None or start_idx < 0:
        start_idx = 0
    ep_count = len(read_and_cache_file(decode_path(ctx.triggered_id)))
    return min(start_idx + 1, ep_count - page_len)

@callback(
    Output(make_generic_id(MATCH, type="epoch-graph-start-idx"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="epoch-graph-fwd-end"), "n_clicks"),
    State(make_generic_id(MATCH, type="epoch-graph-page-len"), "value"),
    prevent_initial_call=True
)
def graph_control_fwd_to_end(_, page_len):
    return len(read_and_cache_file(decode_path(ctx.triggered_id))) - page_len
