import mne
import dash_bootstrap_components as dbc
from .util import plot_to_base64
from dash import html, callback, Input, Output, State, no_update, dcc, MATCH
from io import BytesIO
import base64
# TODO do not include dot
from path_based_id_util import make_id, make_generic_id, decode_path
from file_io import read_and_cache_file
import os

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
    print(kwargs)

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
                                        style={"width": "100%"},
                                    )
                                ) for i, f in enumerate(figs)
                             ]
                        ),
                        dbc.Row(
                            children=dbc.Col(
                                width=12,
                                className="mt-3",
                                children=dcc.Slider(
                                    id=make_id(kwargs["path"], type="esi-slider"),
                                    min=kwargs["tmin"],
                                    max=kwargs["tmax"],
                                    marks={kwargs["initial_time"]: "Peak activity"},
                                    value=kwargs["initial_time"]
                                )
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
        )
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
    return figs
