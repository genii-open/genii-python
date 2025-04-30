import mne
import dash_bootstrap_components as dbc
from .util import plot_to_base64
from dash import html, callback, Input, Output, State, no_update, dcc, MATCH, Patch
from io import BytesIO
import base64
# TODO do not include dot
from path_based_id_util import make_id, make_generic_id, decode_path
from file_io import read_and_cache_file
import os
from plotly.graph_objs import Layout, Scatter, Figure
from plotly.graph_objs.layout import YAxis, Annotation, Font, shape

clientside_collector = tuple()

def render_esi_content(esi: mne.SourceEstimate, 
                    #    surf_esi: mne.SourceEstimate,
                       **kwargs: dict):
    figs = esi_plot_to_base_64(
        esi.plot(
            subjects_dir=kwargs["subjects_dir"],
            show=False,
            initial_time=kwargs["initial_time"],
            src=kwargs["src"],
        ).get_figure()
    )
    # print(kwargs)

    ev_layout = Layout(
        xaxis=dict(showticklabels=False, zeroline=False, showgrid=False),
        yaxis=YAxis(
            showticklabels=True, zeroline=True, showgrid=False, visible=True
        ),
        showlegend=False,
        shapes=[
            dict(
                line=shape.Line(
                    dash="dot",
                    color="green",
                    width=1
                ),
                layer="between",
                x0=kwargs["initial_time"],
                y0=0,
                x1=kwargs["initial_time"],
                y1=1,
                yref="paper",
            )
        ],
        margin=dict(l=20, r=20, t=0, b=0),
        height=200
    )
    ev = read_and_cache_file(kwargs["ev_path"])
    data = ev.get_data()

    traces = [Scatter(
        x=ev.times,
        y=data.T[:, 0],
        line={
            "color": "black",
            "width": 1
        }
    )]

    # loop over the channels
    for ii in range(1, ev.info["nchan"]):
            traces.append(Scatter(
                x=ev.times,
                y=data.T[:, ii],
                line={
                    "color": "black",
                    "width": 1
                }
            ))
    ev_fig = Figure(
        data=traces,
        layout=ev_layout
    )

    # surf_esi.plot(
    #     subject="fsaverage",
    #     hemi="split",
    #     subjects_dir=kwargs["subjects_dir"],
    # ).save_movie("movie.mp4", time_dilation=20, interpolation='linear', framerate=10)

    return (
        "ESI",
        dbc.Row(
            className="max-h-100",
            children=(
                dbc.Col(
                    id=f"main-content-{kwargs['path']}",
                    width=9,
                    children=(
                        dbc.Row(
                            children=[ 
                                dbc.Col(
                                    width=4,
                                    children=html.Img(
                                        id=make_id(kwargs["path"], type=f"img{i}"),
                                        src=f,
                                        style={"width": "70%"},
                                    )
                                ) for i, f in enumerate(figs)
                            ]
                        ),
                        dbc.Row(
                            children=dbc.Col(
                                width=12,
                                className="mt-3 mb-3",
                                children=dcc.Slider(
                                    id=make_id(kwargs["path"], type="esi-slider"),
                                    min=kwargs["tmin"],
                                    max=kwargs["tmax"],
                                    marks={kwargs["initial_time"]: "Peak activity"},
                                    value=kwargs["initial_time"]
                                )
                            )
                        ),
                        dbc.Row(
                            children=dbc.Col(
                                width=12,
                                children=dcc.Graph(
                                    id=make_id(kwargs["path"], type="esi-ev"),
                                    figure=ev_fig
                                ),
                            )
                        )
                    )
                ),
                dbc.Col(
                    className="d-flex flex-column",
                    width=3,
                    children=(
                        "No action available",
                    )
                )
            )
        ),
                
          
    )

# HACK
def esi_plot_to_base_64(fig):
    base64_figs = []
    for i in [2, 3, 4]:
        buffer = BytesIO()
        fig.savefig(buffer, bbox_inches=fig.axes[i].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted()))
        buffer.seek(0)
        data = base64.b64encode(buffer.read()).decode("utf-8")
        buffer.close()
        base64_figs.append("data:image/png;base64,{}".format(data))
    return base64_figs

# HACK
@callback(
    *[Output(make_generic_id(MATCH, type=f"img{i}"), "src") for i in range(3)],
    Output(make_generic_id(MATCH, type="esi-ev"), "figure"),
    Input(make_generic_id(MATCH, type="esi-slider"), "value"),
    State(make_generic_id(MATCH, type="esi-slider"), "id")
)
def redraw(t, id):
    path = decode_path(id)
    stc = read_and_cache_file(path)
    fs_dir = mne.datasets.fetch_fsaverage()
    subjects_dir = os.path.dirname(fs_dir)
    src = os.path.join(fs_dir, "bem", "fsaverage-vol-5-src.fif")
    figs = esi_plot_to_base_64(
        stc.plot(
            subjects_dir=subjects_dir,
            show=False,
            initial_time=t,
            src=src,
        ).get_figure()
    )
    ev_fig_patch = Patch()
    ev_fig_patch["layout"]["shapes"] = [dict(
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
    )]

    return *figs, ev_fig_patch
