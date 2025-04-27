import mne
import dash_bootstrap_components as dbc
from dash import html, callback, Output, Input, State, no_update, ctx, ALL, MATCH, dcc
from .util import plot_to_base64
from file_io import read_and_cache_file, cache_file
from db.data_structure import FileType
import os
from layout_impl.main_body import append_to_tabs 
from workflow.esi import render_esi_content
import numpy as np
from .general import render_general_function

# TODO do not include dot
from path_based_id_util import make_id, make_generic_id, decode_path

from layout_impl.reusable import OnceInterval

from plotly.graph_objs import Layout, Scatter, Figure
from plotly.graph_objs.layout import YAxis, Annotation, Font, shape
from .plotting_util import decide_ch_color, ellipse_arc, head_figure

from scipy.interpolate import CloughTocher2DInterpolator

clientside_collector = (
    (
        "perform-esi-info-collector",
        # FIXME Use ClientsideFunction for sanity
        # NOTE used magic key pth and ext
        # NOTE only 1 trigger allowed
        """
        (i,s,m)=>{
            console.log("EVOKED CC");
            console.log(dash_clientside.callback_context);
            console.log({i, s, m});
            
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
            triggered_id.alg_name = dash_clientside.callback_context.states_list
                .find(
                    s => s[0].id.ext === triggered_id.ext && s[0].id.pth === triggered_id.pth
                )[0].value;
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
        Input(make_generic_id(ALL, type="perform-esi-btn-main"), "n_clicks"),
        State(make_generic_id(ALL, type="perform-esi-btn-dropdown"), "label"),
        State("perform-esi-info-collector", "data"),
    ),
)

_VOLTAGE_MAP_RES = 32

_ESI_ALG_NAMES = ("dSPM", "MNE", "sLORETA", "eLORETA")

def render_evoked_content(file):
    title = "Evoked: " + os.path.basename(file.path)
    if file.dirty:
        title = "*" + title
    peak = file.item.get_peak()[1]
    content = dbc.Row(
        className="max-h-100",
        children=(
            dbc.Col(
                width=3,
                children=(
                    dcc.Loading(
                        id=make_id(file.path, type="evoked-ch-graph-loading"),
                        className="h-100",
                        display="show",
                        children=(
                            dcc.Graph(
                                id=make_id(file.path, type="evoked-ch-graph"),
                            ),
                            dcc.Slider(
                                id=make_id(file.path, type="evoked-t"),
                                min=file.item.tmin,
                                max=file.item.tmax,
                                value=peak,
                                step=0.01,
                                marks={
                                    file.item.tmin: {"label": f"{file.item.tmin: .2f}"},
                                    peak: {"label": f"{peak: .2f}"},
                                    file.item.tmax: {"label": f"{file.item.tmin: .2f}"},
                                },
                                included=False
                            ),
                            # dcc.Input(
                            #     id=make_id(file.path, type="evoked-t"),
                            #     type="number",
                            #     value=file.item.get_peak()[1]
                            # )
                        )
                    )
                )
            ),
            dbc.Col(
                # id=make_id(file.path, type="evoked-main-content"),
                width=6,
                className="d-flex flex-column",
                children=(
                    dcc.Loading(
                        id=make_id(file.path, type="evoked-topomap-loading"),
                        className="w-100 h-100",
                        display="show",
                        children=(
                            dcc.Graph(
                                id=make_id(file.path, type="evoked-topomap")
                            ),
                        )
                    ),
                    # html.Img(
                    #     src=plot_to_base64(file.item.plot_joint(show=False).get_figure()),
                    #     className="max-w-100"
                    # ),
                    # html.Img(
                    #     src=plot_to_base64(
                    #         file.item.plot_topomap(
                    #             times=np.concatenate((np.linspace(file.item.tmin, 0, 2), np.linspace(0, file.item.tmax, 4)[1:])) ,
                    #             show=False
                    #         ).get_figure()),
                    #     className="max-w-100",
                    # )
                )
            ),
            dbc.Col(
                className="d-flex flex-column",
                width=3,
                children=(
                    render_general_function(file),
                    dbc.ButtonGroup(
                        children=(
                            dbc.Button(
                                id=make_id(file.path, type="perform-esi-btn-main"),
                                className="text-end",
                                children="Perform ESI with "
                            ),
                            dbc.DropdownMenu(
                                id=make_id(file.path, type="perform-esi-btn-dropdown"),
                                label="dSPM",
                                group=True,
                                children=[
                                    dbc.DropdownMenuItem(
                                        # FIXME this looks stupid
                                        id=make_id(file.path, type="perform-esi-btn-dropdown-item", index=alg_name),
                                        children=alg_name
                                    ) for alg_name in _ESI_ALG_NAMES
                                ]
                                    # dbc.DropdownMenuItem("ECD"),
                            ),
                        )
                    ),
                )
            ),
            OnceInterval(id=make_id(file.path, type="evoked-once-interval"))
        )
    )
    return title, content

# TODO copied from raw, can be pulled into a plot util or sth
# FIXME scale of signal
@callback(
    Output(make_generic_id(MATCH, type="evoked-ch-graph"), "figure"),
    Output(make_generic_id(MATCH, type="evoked-ch-graph-loading"), "display"),
    Input(make_generic_id(MATCH, type="evoked-once-interval"), "n_intervals"),
    Input(make_generic_id(MATCH, type="evoked-t"), "value"),
    State(make_generic_id(MATCH, type="evoked-once-interval"), "id"),
)
def render_evoked_graph(_, t, id):
    path = decode_path(id)
    evoked = read_and_cache_file(path)

    if t is None:
        t = evoked.get_peak()[1]
    t = max(evoked.tmin, min(evoked.tmax, t))


    data = evoked.get_data()
    # view = evoked.info.get("temp", {}).get("view", None)
    # if view is None:
    #     data = evoked.get_data()
    # else:
    #     data = view.get_data()

    step = 1. / evoked.info["nchan"]
    kwargs = dict(domain=[1 - step, 1], showticklabels=False, zeroline=False, showgrid=False, visible=False)

    # create objects for layout and traces
    # FIXME unable to show time at the bottom
    layout = Layout(
        xaxis=dict(showticklabels=False, zeroline=False, showgrid=False),
        yaxis=YAxis(kwargs), showlegend=False,
        shapes=[
            dict(
                line=shape.Line(
                    dash="dot",
                    color="green",
                    width=1
                ),
                layer="between",
                x0=t,
                y0=0,
                x1=t,
                y1=1,
                yref="paper",
            )
        ]
    )
    traces = [Scatter(
        x=evoked.times,
        y=data.T[:, 0],
        line={
            "color": decide_ch_color(evoked.info["ch_names"][0], evoked.info["bads"]),
            "width": 1
        }
    )]

    # loop over the channels
    for ii in range(1, evoked.info["nchan"]):
            kwargs.update(domain=[1 - (ii + 1) * step, 1 - ii * step])
            layout.update({'yaxis%d' % (ii + 1): YAxis(kwargs), 'showlegend': False})
            traces.append(Scatter(
                x=evoked.times,
                y=data.T[:, ii],
                yaxis='y%d' % (ii + 1),
                line={
                    "color": decide_ch_color(evoked.info["ch_names"][ii], evoked.info["bads"]),
                    "width": 1
                }
            ))

    # add channel names using Annotations
    annotations = [
        Annotation(
            x=-0.16, y=0, xref='paper', yref='y%d' % (ii + 1),
            text=ch_name,
            showarrow=False
        ) for ii, ch_name in enumerate(evoked.info["ch_names"])
    ]



    layout.update(annotations=annotations, margin=dict(l=40, r=20, t=20, b=20))
    fig = Figure(data=traces, layout=layout)

    return fig, "hide"


@callback(
    Output(make_generic_id(MATCH, type="evoked-topomap"), "figure"),
    Output(make_generic_id(MATCH, type="evoked-topomap-loading"), "display"),
    Input(make_generic_id(MATCH, type="evoked-once-interval"), "n_intervals"),
    Input(make_generic_id(MATCH, type="evoked-t"), "value"),
    State(make_generic_id(MATCH, type="evoked-once-interval"), "id"),
)
def render_init_evoked_topomap(_, t, id):
    path = decode_path(id)
    evoked = read_and_cache_file(path)
    
    if t is None:
        t = evoked.get_peak()[1]
    t = max(evoked.tmin, min(evoked.tmax, t))

    fig = head_figure(evoked.info["dig"], evoked, t, _VOLTAGE_MAP_RES)    
    return fig, "hide"

# @callback(
#     Output(make_generic_id(MATCH, type="evoked-topomap"), "figure", allow_duplicate=True),
#     Input(make_generic_id(MATCH, type="evoked-t"), "value"),
#     State(make_generic_id(MATCH, type="evoked-topomap"), "figure"),
#     prevent_initial_callback=True,
#     running=(
#         (Output(make_generic_id(MATCH, type="evoked-topomap-loading"), "display"), "show", "hide"),
#     )
# )
# def AAAAAAAA(time, fig):
#     if not ctx.triggered_id:
#         return no_update
#     path = decode_path(ctx.triggered_id)
#     evoked = read_and_cache_file(path)
#     print(fig)
    # Start voltage map plotting
    # intp = CloughTocher2DInterpolator(
    #     np.column_stack((data_x,data_y)),
    #     evoked.get_data()[:, evoked.time_as_index(time).item()]
    # )
    # x=np.linspace(axis_x_range[0], axis_x_range[1], res),
    # y=np.linspace(axis_y_range[0], axis_y_range[1], res),
    # xv, yv = np.meshgrid(x, y)
    # coord = np.column_stack((xv.reshape(-1),yv.reshape(-1)))
    # heatmap = Heatmap(
    #     x=x, y=y,
    #     z=intp(coord)
    # )
    # return no_update

# TODO clientside
@callback(
    Output(make_generic_id(MATCH, type="perform-esi-btn-dropdown"), "label"),
    Input(make_generic_id(MATCH, type="perform-esi-btn-dropdown-item", index=ALL), "n_clicks"),
    prevent_initial_call=True
)
def change_chosen_alg(_):
    return ctx.triggered_id["index"]

@callback(
    Output("content-tabs", "children", allow_duplicate=True),
    Output("content-tabs", "value", allow_duplicate=True),
    Input("perform-esi-info-collector", "data"),
    State({"type": "content-tab-list", "index": ALL}, "value"),
    prevent_initial_call=True
)
def perform_esi(info, tab_values):
    # print(info)
    if info is None:
        return no_update
    
    if "alg_name" not in info.keys() or info["alg_name"] is None:
        return no_update # TODO error message choose an algorithm
    
    path = decode_path(info)

    # ep = read_and_cache_file("-epo.".join(path.split(".")))
    ep = read_and_cache_file(path[:-7]+"epo.fif")
    ev = read_and_cache_file(path)

    fs_dir = mne.datasets.fetch_fsaverage()
    subjects_dir = os.path.dirname(fs_dir)
    trans = "fsaverage"
    src = os.path.join(fs_dir, "bem", "fsaverage-vol-5-src.fif")
    bem = os.path.join(fs_dir, "bem", "fsaverage-5120-5120-5120-bem-sol.fif")
    fwd = mne.make_forward_solution(ep.info, trans=trans, src=src, bem=bem, eeg=True, mindist=5.0, n_jobs=None)
    cov = mne.compute_covariance(ep, tmax=0.0)
    inv = mne.minimum_norm.make_inverse_operator(ev.info, fwd, cov, verbose=True)
    stc = mne.minimum_norm.apply_inverse(ev, inv, method=info["alg_name"])

    # src2 = os.path.join(fs_dir, "bem", "fsaverage-ico-5-src.fif")
    # fwd2 = mne.make_forward_solution(ep.info, trans=trans, src=src2, bem=bem, eeg=True, mindist=5.0, n_jobs=None)
    # inv2 = mne.minimum_norm.make_inverse_operator(ev.info, fwd2, cov, verbose=True)
    # stc2 = mne.minimum_norm.apply_inverse(ev, inv2, method=info["alg_name"])
    
    stc_path = path + ".stc"
    # stc2_path = path + "-surf.stc"
    cache_file(stc, FileType.ESI, True, stc_path)
    # cache_file(stc2, FileType.ESI, True, stc2_path)
    return append_to_tabs(tab_values, *render_esi_content(stc, path=stc_path, subjects_dir=subjects_dir, src=src, initial_time=ev.get_peak(ch_type="eeg")[1], tmin=ev.tmin, tmax=ev.tmax))
