from dash import html, dcc

# An Interval object that only run once
# To make sure that a callback is only executed once
# Use Input(id, "n_intervals") to subscribe to the element
# https://stackoverflow.com/a/71518196
def OnceInterval(id):
    return dcc.Interval(
        id=id,
        n_intervals=0,
        max_intervals=0,
        interval=1
    )

# A "button" with outlined close icon
# Will be changed to filled close icon on hover
# Dash does not support callback on hover, so this is done via CSS hack
# See static/style.css .tab-close-icon
def FillOnHoverCloseTabBtn(id):
    return html.Span(
        id=id,
        role="button",
        className="tab-close-icon",
        title="Close this tab",
    )