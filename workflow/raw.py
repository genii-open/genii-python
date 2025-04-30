import mne
from dash import dcc, html, callback, Output, Input, State, no_update, ctx, MATCH, ALL, Patch
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from .util import plot_to_base64
from layout_impl.main_body import append_to_tabs
from .epoch import render_epoch_content
from file_io import read_and_cache_file, cache_file
from db.data_structure import File, FileType
import os

# import chart_studio.plotly as py
from plotly import tools
from plotly.graph_objs import Layout, Scatter, Figure
from plotly.graph_objs.layout import YAxis, Annotation, Font, shape
from layout_impl.reusable import OnceInterval

from .general import render_general_function

from path_based_id_util import make_id, make_generic_id, decode_path

from datetime import datetime

from .plotting_util import decide_ch_color, _BAD_CH_LINE_COLOR, _DEFAULT_CH_LINE_COLOR

# FIXME this can be broken into separete files but I am lazy
# One file for layout, one for callback, one for implementing the processing/plotting logic

_ADD_NEW_EVENT_DROPDOWN_OPTION_VALUE = "___add___create___new___"

_PAGE_LEN = 10

_EPOCHING_TMIN = -0.2
_EPOCHING_TMAX = 0.5

clientside_collector = (
    (
        "extract-epoch-info-collector",
        # FIXME Use ClientsideFunction for sanity
        # What is worse than js? js without syntax highlighting
        # Also it gives you the most cryptic error message in the popup thing, need to check console for the actual error
        # NOTE used magic key pth and ext
        # NOTE only 1 trigger allowed
        """
        (i,s,m)=>{
            console.log("RAW CC");
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
            triggered_id.ev_name = dash_clientside.callback_context.states_list[0]
                .find(
                    s => s.id.ext === triggered_id.ext && s.id.pth === triggered_id.pth
                ).value;
            triggered_id.tmin = dash_clientside.callback_context.states_list[1]
                .find(
                    s => s.id.ext === triggered_id.ext && s.id.pth === triggered_id.pth
                ).value;
            triggered_id.tmax = dash_clientside.callback_context.states_list[2]
                .find(
                    s => s.id.ext === triggered_id.ext && s.id.pth === triggered_id.pth
                ).value;
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
        Input(make_generic_id(ALL, type="extract-epoch-btn"), "n_clicks"),
        State(make_generic_id(ALL, type="raw-event-select"), "value"),
        State(make_generic_id(ALL, type="raw-epoching-tmin"), "value"),
        State(make_generic_id(ALL, type="raw-epoching-tmax"), "value"),
        State("extract-epoch-info-collector", "data"),
    ),
)

def render_raw_content(file: File):
    title = "Raw: " + os.path.basename(file.path)
    if file.dirty:
        title = "*" + title
    # NOTE automatically perform averaged reference

    # file.item.drop_channels(['T1', 'T2', 'X28', 'X29', 'X30', 'X31', 'X32', 'ECG-LA', 'ECG-RA', 'ECG-LL', 'ECG-V1', 'ECG-V2', 'EOG1', 'EOG2', 'EMG1', 'EMG2', 'CHINz', 'HV+', 'HV1-', 'DIF2+', 'DIF2-', 'DIF3+', 'DIF3-', 'DIF4+', 'DIF4-', 'DIF5+', 'DIF5-', 'DIF6+', 'DIF6-', 'DIF7+', 'DIF7-', 'DIF8+', 'DIF8-', 'DIF9+', 'DIF9-', 'DIF10+', 'DIF10-', 'RLEG+', 'RLEG-', 'LLEG+', 'LLEG-', 'Snore', 'Flow', 'Pressure', 'Flow_DR', 'Snore_DR', 'Abdomen', 'Chest', 'Phase', 'RMI', 'RR', 'XSum', 'XFlow', 'XVolume', 'Position', 'Elevation', 'Activity', 'PPG', 'PTT', 'Pleth', 'DC13', 'DC14', 'DC15', 'DC16', 'DC1', 'DC2', 'DC3', 'DC4', 'DC5', 'DC6', 'DC7', 'DC8', 'DC9', 'DC10', 'DC11', 'DC12', 'TRIG', 'SpO2', 'PR', 'PulseQuality'])
    montage = mne.channels.make_standard_montage("standard_1020")
    # file.item.drop_channels(list(set(file.item.ch_names) - montage.ch_names))
    file.item.set_montage(montage, match_case=False, match_alias=True, on_missing="ignore")
    file.item.load_data().set_eeg_reference(projection=True)
    cache_file(file.item, FileType.RAW, False, file.path)
    content = dbc.Row(
        className="max-h-100",
        children=(
            dbc.Col(
                # id=make_id(file.path, type="raw-main-content"),
                width=9,
                children=(
                    dcc.Loading(
                        id=make_id(file.path, type="raw-graph-loading"),
                        className="h-100",
                        display="show",
                        children=(
                            dcc.Graph(
                                id=make_id(file.path, type="raw-graph"),
                            ),
                            dbc.InputGroup(
                                # id=make_id(file.path, type="raw-graph-control"),
                                children=(
                                    dbc.Button(
                                        id=make_id(file.path, type="raw-graph-back-start"),
                                        children=DashIconify(icon="gg:play-backwards"),
                                        title="Move to the start of file"
                                    ),
                                    dbc.Button(
                                        id=make_id(file.path, type="raw-graph-back-page"),
                                        children=DashIconify(icon="gg:play-track-prev"),
                                        title="Move back half page"
                                    ),
                                    dbc.Input(
                                        id=make_id(file.path, type="raw-graph-page-len"),
                                        type="number",
                                        value=_PAGE_LEN,
                                        min=0.5
                                    ),
                                    dbc.InputGroupText("sec"),
                                    dbc.Button(
                                        id=make_id(file.path, type="raw-graph-fwd-page"),
                                        children=DashIconify(icon="gg:play-track-next"),
                                        title="Move forward half page"
                                    ),
                                    dbc.Button(
                                        id=make_id(file.path, type="raw-graph-fwd-end"),
                                        children=DashIconify(icon="gg:play-forwards"),
                                        title="Move to the start of file"
                                    ),
                                    dcc.Store(
                                        id=make_id(file.path, type="raw-graph-tmin"),
                                        clear_data=True,
                                        data=0
                                    )
                                )
                            )
                        )
                    )
                )
            ),
            dbc.Col(
                className="d-flex flex-column",
                width=3,
                children=(
                    render_general_function(file),
                    dmc.Switch(
                        id=make_id(file.path, type="raw-graph-annotation-switch"),
                        label="Annotation Mode",
                        size="lg",
                        checked=False
                    ),
                    dcc.Dropdown(
                        id=make_id(file.path, type="raw-event-select"),
                        value=None,
                        options=[{"label":"Loading...", "value": False}],
                        disabled=True,
                        clearable=False
                    ),
                    dbc.InputGroup(
                        children=(
                            dbc.Input(
                                id=make_id(file.path, type="raw-epoching-tmin"),
                                type="number",
                                max=0,
                                value=_EPOCHING_TMIN
                            ),
                            dbc.InputGroupText(children="~"),
                            dbc.Input(
                                id=make_id(file.path, type="raw-epoching-tmax"),
                                type="number",
                                min=0,
                                value=_EPOCHING_TMAX
                            )
                        )
                    ),
                    dbc.Button(
                        id=make_id(file.path, type="extract-epoch-btn"),
                        children="Extract Epochs...",
                        disabled=True
                    )
                )
            ),
            OnceInterval(make_id(file.path, type="raw-once-interval"))
        )
    )
    return title, content

@callback(
    Output(make_generic_id(MATCH, type="raw-graph"), "figure"),
    Output(make_generic_id(MATCH, type="raw-graph-loading"), "display"),
    Input(make_generic_id(MATCH, type="raw-once-interval"), "n_intervals"),
    Input(make_generic_id(MATCH, type="raw-graph-tmin"), "data"),
    Input(make_generic_id(MATCH, type="raw-graph-page-len"), "value"),
    State(make_generic_id(MATCH, type="raw-once-interval"), "id"),
)
def render_raw_graph(_, tmin, page_len, id):
    if not page_len or page_len <= 0:
        page_len = _PAGE_LEN
    if not tmin or tmin < 0:
        tmin = 0
    tmax = tmin + page_len
    path = decode_path(id)
    raw = read_and_cache_file(path)

    # view = raw.info.get("temp", {}).get("view", None)
    # if view is not None:
    #     raw = view

    start, stop = raw.time_as_index([tmin, tmax])
    data, times = raw[:, start:stop]
    
    step = 1. / raw.info["nchan"]
    kwargs = dict(domain=[1 - step, 1], showticklabels=False, zeroline=False, showgrid=False, visible=False)

    # create objects for layout and traces
    # FIXME unable to show time at the bottom
    layout = Layout(
        xaxis=dict(showticklabels=False, zeroline=False),
        yaxis=YAxis(kwargs), showlegend=False
    )
    traces = [Scatter(
        x=times,
        y=data.T[:, 0],
        line={
            "color": decide_ch_color(raw.info["ch_names"][0], raw.info["bads"]),
            "width": 1
        }
    )]

    # loop over the channels
    for ii in range(1, raw.info["nchan"]):
            kwargs.update(domain=[1 - (ii + 1) * step, 1 - ii * step])
            layout.update({'yaxis%d' % (ii + 1): YAxis(kwargs), 'showlegend': False})
            traces.append(Scatter(
                x=times,
                y=data.T[:, ii],
                yaxis='y%d' % (ii + 1),
                line={
                    "color": decide_ch_color(raw.info["ch_names"][ii], raw.info["bads"]),
                    "width": 1
                }
            ))

    # add channel names using Annotations
    annotations = [
        Annotation(
            x=-0.06, y=0, xref='paper', yref='y%d' % (ii + 1),
            text=ch_name,
            showarrow=False
        ) for ii, ch_name in enumerate(raw.info["ch_names"])
    ]

    layout.update(annotations=annotations, margin=dict(l=60, r=20, t=20, b=20))
    fig = Figure(data=traces, layout=layout)
    
    for ann in raw.annotations.copy().crop(tmin, tmax, use_orig_time=False):
        fig.add_shape(
            line=shape.Line(
                dash="dot",
                color="green",
                width=1
            ),
            layer="between",
            x0=ann["onset"],
            y0=0,
            x1=ann["onset"],# TODO + ann["duration"],
            y1=1,
            yref="paper",
            label=shape.Label(
                text=ann["description"],
                textposition="top center"
            )
        )

    return fig, "hide"

@callback(
    Output(make_generic_id(MATCH, type="raw-event-select"), "options"),
    Output(make_generic_id(MATCH, type="raw-event-select"), "disabled"),
    Output(make_generic_id(MATCH, type="raw-event-select"), "value"),
    Output(make_generic_id(MATCH, type="extract-epoch-btn"), "disabled"),
    Input(make_generic_id(MATCH, type="raw-once-interval"), "n_intervals"),
    State(make_generic_id(MATCH, type="raw-once-interval"), "id"),
)
def update_event_options(_, id):
    path = decode_path(id)
    raw = read_and_cache_file(path)
    return  [
        {
            "label": html.Span(
                children=dbc.Input(
                    id=make_id(path, type="new-event-input"),
                    type="text",
                    className="border-0 shadow-none ps-0 bg-transparent",
                    placeholder="New..."
                )
            ),
            "value": _ADD_NEW_EVENT_DROPDOWN_OPTION_VALUE
        },
        *[{
            "label": e,
            "value": e
        } for e in raw.annotations.count().keys()]
    ], False, _ADD_NEW_EVENT_DROPDOWN_OPTION_VALUE, False


@callback(
    Output(make_generic_id(MATCH, type="raw-graph"), 'figure', allow_duplicate=True),
    Output(make_generic_id(MATCH, type="raw-event-select"), "options", allow_duplicate=True),
    Output(make_generic_id(MATCH, type="raw-event-select"), "value", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="raw-graph"), 'clickData'),
    # State(make_generic_id(MATCH, type="raw-graph"), 'figure'),
    State(make_generic_id(MATCH, type="raw-graph-annotation-switch"), "checked"),
    State(make_generic_id(MATCH, type="raw-event-select"), "value"),
    State(make_generic_id(MATCH, type="new-event-input"), "value"),
    State(make_generic_id(MATCH, type="raw-event-select"), "options"),
    State(make_generic_id(MATCH, type="raw-graph-tmin"), "data"),
    State(make_generic_id(MATCH, type="raw-graph-page-len"), "value"),
    prevent_initial_call=True
)
# FIXME Double click on the same point will not trigger callback
# Because forntend do not consider the same/near click point data to be a "state change"
# Even after you moved the pointer away and back 
# So it will not send a request to backend
def handle_click_data(clickData, checked, ev_select, new_ev, curr_ev, tmin, page_len):
    if tmin is None or tmin < 0:
        tmin = 0
    if page_len is None or page_len <= 0:
        page_len = _PAGE_LEN
    if checked:
        return handle_annotate(clickData, ev_select, new_ev, curr_ev, tmin, page_len)
    else:
        return handle_toggle_bad_ch(clickData), no_update, no_update

def handle_annotate(clickData, ev_select, new_ev, curr_ev, tmin, page_len):
    # print(clickData)
    have_new_ev = ev_select == _ADD_NEW_EVENT_DROPDOWN_OPTION_VALUE
    path = decode_path(ctx.triggered_id)
    raw = read_and_cache_file(path)

    # fig = Figure(fig_data)
    fig = Patch()

    if clickData and clickData['points']:
        # 获取点击的 x 坐标（即时间点）
        click_x = clickData['points'][0]['x']

        # 检查是否已有记录线在相同位置，如果有则删除
        # If distance < 1%, then it is close enough
        # Also only delete the closest one
        # one_percent = (fig_data["layout"]["xaxis"]["range"][1] - fig_data["layout"]["xaxis"]["range"][0]) / 100
        one_percent = page_len / 100
        closest_line = None
        closest_dist = None
        # for line in fig.layout.shapes:
        #     # TODO check is line
        #     dist = abs(line['x0'] - click_x)
        #     if dist < one_percent and (closest_dist is None or closest_dist > dist):
        #         closest_line = line
        #         closest_dist = dist
        # if closest_line is not None:
        #     # 删除已有的标注线
        #     # print(closest_line)
        #     for i, a in enumerate(raw.annotations):
        #         if a["onset"] - closest_line["x0"] < 1e-5 and a["description"] == closest_line["label"]["text"]:
        #             raw.annotations.delete(i)
        #             break
        #     fig.layout.shapes = [line for line in fig.layout.shapes if line['x0'] != closest_line["x0"]]
        for i, a in enumerate(raw.annotations): # FIXME can optimize
            dist = abs(a["onset"] - click_x)
            if dist < one_percent and (closest_dist is None or closest_dist > dist):
                closest_line = i
                closest_dist = dist
        if closest_line is not None:
            raw.annotations.delete(closest_line)
            fig_shape = []
            for ann in raw.annotations.copy().crop(tmin, tmin + page_len, use_orig_time=False):
                # FIXME copy pasted
                fig_shape.append(dict(
                    line=shape.Line(
                        dash="dot",
                        color="green",
                        width=1
                    ),
                    layer="between",
                    x0=ann["onset"],
                    y0=0,
                    x1=ann["onset"],# TODO + ann["duration"],
                    y1=1,
                    yref="paper",
                    label=shape.Label(
                        text=ann["description"],
                        textposition="top center"
                    )
                ))
            fig["layout"]["shapes"] = fig_shape
        else:
            # 添加新的标注线
            # FIXME copy pasted
            if have_new_ev:
                if new_ev is None:
                    return no_update
                    #TODO error when input is empty
                if isinstance(curr_ev, list):
                    curr_ev.append({"label": new_ev, "value": new_ev})
                else:
                    curr_ev = [new_ev]
                ev_select = new_ev
                curr_ev[0]["label"]["props"]["children"]["props"]["value"] = None
            fig["layout"]["shapes"].append(dict(
                line=shape.Line(
                    dash="dot",
                    color="green",
                    width=1
                ),
                layer="between",
                x0=click_x, y0=0, x1=click_x, y1=1, yref="paper",
                label=shape.Label(
                    text=ev_select,
                    textposition="top center"
                )
            ))
            raw.annotations.append(click_x, 0, ev_select) # TODO support of duration
            # if have_new_ev:
            #     curr_ev = [curr_ev[0], *[{"label": e, "value": e} for e in raw.annotations.count().keys()]]

    cache_file(raw, FileType.RAW, True, path)

    return fig, no_update if not have_new_ev else curr_ev, no_update if not have_new_ev else ev_select

def handle_toggle_bad_ch(clickData):
    path = decode_path(ctx.triggered_id)
    raw = read_and_cache_file(path)
    ch_idx = clickData["points"][0]["curveNumber"]
    ch_n = raw.ch_names[ch_idx]
    if ch_n in raw.info["bads"]:
        color = _DEFAULT_CH_LINE_COLOR
        raw.info["bads"].remove(ch_n)
    else:
        color = _BAD_CH_LINE_COLOR
        raw.info["bads"].append(ch_n)
    fig_data = Patch()
    fig_data["data"][ch_idx]["line"]["color"]=color
    cache_file(raw, FileType.RAW, True, path)
    return fig_data

@callback(
    Output("content-tabs", "children", allow_duplicate=True),
    Output("content-tabs", "value", allow_duplicate=True),
    Input("extract-epoch-info-collector", "data"),
    State({"type": "content-tab-list", "index": ALL}, "value"),
    prevent_initial_call=True
)
def extract_epoch(info, tab_values):
    # print("AAAAAAAAAAAAAAAAAAAAAA")
    # print(info)
    # print(path)
    # print(state)
    if info is None:
        return no_update
    
    if "ev_name" not in info.keys() or info["ev_name"] is None:
        return no_update # TODO error message event name is required
    
    if info["ev_name"] == _ADD_NEW_EVENT_DROPDOWN_OPTION_VALUE:
        return no_update # TODO new event not allowed
    
    if info["tmin"] is None or info["tmin"] >= 0:
        info["tmin"] = _EPOCHING_TMIN
    if info["tmax"] is None or info["tmax"] <= 0:
        info["tmax"] = _EPOCHING_TMAX

    path = decode_path(info)
    raw = read_and_cache_file(path)
    ep = mne.Epochs(raw, event_repeated="merge", tmin=info["tmin"], tmax=info["tmax"])[info["ev_name"]]
    ep.load_data().drop_bad()
    # if "temp" in ep.info:
    #     del ep.info["temp"]
    # ep_path = os.path.join(os.path.dirname(path), os.path.basename(path).split(".")[0]) + "-" + datetime.now().strftime("%d_%m_%y__%H_%M_%S") + "-epo.fif"
    ep_path = os.path.join(os.path.dirname(path), os.path.basename(path).split(".")[0]) + "-epo.fif"
    ep.save(ep_path, overwrite=True)
    ep = cache_file(ep, FileType.EPOCH, True, ep_path)
    return append_to_tabs(tab_values, *render_epoch_content(ep))

# TODO stuff like this should be clientside callback but I am lazy
# This implementation cause 2 round trips for 1 graph update
@callback(
    Output(make_generic_id(MATCH, type="raw-graph-tmin"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="raw-graph-back-start"), "n_clicks"),
    prevent_initial_call=True
)
def graph_control_back_to_start(_):
    return 0

@callback(
    Output(make_generic_id(MATCH, type="raw-graph-tmin"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="raw-graph-back-page"), "n_clicks"),
    State(make_generic_id(MATCH, type="raw-graph-tmin"), "data"),
    State(make_generic_id(MATCH, type="raw-graph-page-len"), "value"),
    prevent_initial_call=True
)
def graph_control_back_half_page(_, tmin, page_len):
    if tmin is None or tmin < 0:
        tmin = 0
    if page_len is None or page_len <= 0:
        page_len = _PAGE_LEN
    return max(tmin - 0.5 * page_len, 0)

@callback(
    Output(make_generic_id(MATCH, type="raw-graph-tmin"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="raw-graph-fwd-page"), "n_clicks"),
    State(make_generic_id(MATCH, type="raw-graph-tmin"), "data"),
    State(make_generic_id(MATCH, type="raw-graph-page-len"), "value"),
    prevent_initial_call=True
)
def graph_control_fwd_half_page(_, tmin, page_len):
    if tmin is None or tmin < 0:
        tmin = 0
    if page_len is None or page_len <= 0:
        page_len = _PAGE_LEN
    tmax = read_and_cache_file(decode_path(ctx.triggered_id)).times[-1]
    return min(tmin + 0.5 * page_len, tmax - page_len)

@callback(
    Output(make_generic_id(MATCH, type="raw-graph-tmin"), "data", allow_duplicate=True),
    Input(make_generic_id(MATCH, type="raw-graph-fwd-end"), "n_clicks"),
    State(make_generic_id(MATCH, type="raw-graph-page-len"), "value"),
    prevent_initial_call=True
)
def graph_control_fwd_to_end(_, page_len):
    return read_and_cache_file(decode_path(ctx.triggered_id)).times[-1] - page_len
