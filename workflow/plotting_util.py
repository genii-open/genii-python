import numpy as np

from plotly.graph_objs import Layout, Scatter, Figure, Contour
from plotly.graph_objs.layout import XAxis, YAxis, Annotation, Font, shape

from scipy.interpolate import CloughTocher2DInterpolator

_BAD_CH_LINE_COLOR = "lightgrey"
_DEFAULT_CH_LINE_COLOR = "black"


def decide_ch_color(ch_name, bads):
    return _BAD_CH_LINE_COLOR if ch_name in bads else _DEFAULT_CH_LINE_COLOR

def head_figure(ch_loc, evoked, time, res):
    # FIXME shouls check the type of points
    # FIXME instead of scaling & offset the coord, try scale the shapes
    # FIXME because current approach is scaling coord, cannot separate plot_head and plot_voltage_map
    ch_loc = evoked.info["chs"]
    data_x = np.array([c["loc"][0] for c in ch_loc]) * 10
    data_y = np.array([c["loc"][1] for c in ch_loc]) * 10
    data_name = [c["ch_name"] for c in ch_loc]
    center = np.argmin(data_x ** 2 + data_y ** 2)
    data_x -= data_x[center]
    data_y -= data_y[center]

    # FIXME assume leftmost is at ear (true center)
    leftmost_y = data_y[np.argmin(data_x)]
    data_y -= leftmost_y

    axis_x_range = (-1.2, 1.2)
    axis_y_range = (-1.2, 1.2)

    ch_scatter = Scatter(
        x=data_x,
        y=data_y,
        mode="markers+text", 
        textposition="top center",
        text=data_name,
        marker=dict(
            color='black',
            size=10,
        ),
    )

    layout = Layout(
        xaxis={
            "range": axis_x_range,
            "showticklabels": False,
            "zeroline": False,
            "showgrid": False,
            "visible": False
        },
        yaxis={
            "range": axis_y_range,
            "scaleanchor": "x",
            "scaleratio": 1,
            "showticklabels": False,
            "zeroline": False,
            "showgrid": False,
            "visible": False
        },
        shapes=[
            # Head
            {
                "type": "circle",
                "x0":-1, "y0":-1, "x1":1, "y1":1,
            },
            # Nose
            {
                "type": "line",
                "x0":-0.1, "y0":0.99498743710662, "x1":0, "y1":1.1,
            },
            {
                "type": "line",
                "x0":0.1, "y0":0.99498743710662, "x1":0, "y1":1.1,
            },
            # Left ear
            {
                "type": "line",
                "x0":-0.9886859966642595, "y0":0.15, "x1":-1.05, "y1":0.15,
            },
            {
                "type": "line",
                "x0":-1.05, "y0":0.15, "x1":-1.05, "y1":-0.15,
            },
            {
                "type": "line",
                "x0":-0.9886859966642595, "y0":-0.15, "x1":-1.05, "y1":-0.15,
            },
            # Right ear
            {
                "type": "line",
                "x0":0.9886859966642595, "y0":0.15, "x1":1.05, "y1":0.15,
            },
            {
                "type": "line",
                "x0":1.05, "y0":0.15, "x1":1.05, "y1":-0.15,
            },
            {
                "type": "line",
                "x0":0.9886859966642595, "y0":-0.15, "x1":1.05, "y1":-0.15,
            },
        ],
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
    )

    # Start voltage map plotting
    intp = CloughTocher2DInterpolator(
        np.column_stack((data_x, data_y)),
        evoked.get_data()[:, evoked.time_as_index(time).item()]
    )
    x = np.linspace(axis_x_range[0], axis_x_range[1], res)
    y = np.linspace(axis_y_range[0], axis_y_range[1], res)
    xv, yv = np.meshgrid(x, y)
    coord = np.column_stack((xv.reshape(-1),yv.reshape(-1)))
    z = intp(coord).reshape(res, res)
    contour = Contour(
        x=x, y=y,
        z=z,
        connectgaps=True,
        colorscale="RdBu_r",
        zmin=np.min(evoked.get_data()),
        zmax=np.max(evoked.get_data())
    )

    fig = Figure(data=[contour, ch_scatter], layout=layout)
    
    return fig

# https://community.plotly.com/t/arc-shape-with-path/7205/5
def ellipse_arc(x_center=0, y_center=0, a=1, b =1, start_angle=0, end_angle=2*np.pi, N=100, closed=False):
    t = np.linspace(start_angle, end_angle, N)
    x = x_center + a*np.cos(t)
    y = y_center + b*np.sin(t)
    path = f'M {x[0]}, {y[0]}'
    for k in range(1, len(t)):
        path += f'L{x[k]}, {y[k]}'
    if closed:
        path += ' Z'
    return path  