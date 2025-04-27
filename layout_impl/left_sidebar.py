from flask import g
from dash_iconify import DashIconify
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import callback, Input, Output, ALL, MATCH, State, ctx, no_update, html, dcc, Patch
import os
from file_io import read_check_and_cache_file, read_summary_and_cache_file, infer_file_type, validate_access
from db.data_structure import FileType
from workflow.raw import render_raw_content
from workflow.epoch import render_epoch_content
from workflow.evoked import render_evoked_content
from workflow.esi import render_esi_content
import traceback
from path_based_id_util import make_id, make_generic_id, decode_path
from.main_body import append_to_tabs
from time import time
from db.memcached_util import remove_cache, _CACHE_DIR

from glob import glob
from pathlib import Path

left_sidebar_class_name = "d-flex flex-column bg-light h-100"

def left_sidebar():
    return dbc.Col(
        id="left-sidebar",
        className=left_sidebar_class_name,
        width=2,
        children=(
            # dbc.Button(id="test-btn"),
            dbc.Container(
                id="workspace-file-list",
                className="bg-body h-50 m-1 overflow-auto"
            ),
            dbc.Container(
                id="workspace-file-summary",
                className="bg-body h-50 m-1",
                children=(
                    dcc.Loading(
                        id="workspace-summary-loading",
                        display="hide",
                        className="h-100",
                        children=(
                            dbc.Container(
                                id="workspace-file-summary-content",
                                className="bg-body",
                                children=render_default_workspace_summary_content()
                            ),
                            dbc.ButtonGroup(
                                id="file-controls",
                                className="d-none",
                                children=(
                                    dbc.Button(
                                        id="delete-file-btn",
                                        className="btn btn-outline-danger",
                                        title="Delete",
                                        children=DashIconify(icon="fluent-mdl2:delete")
                                    ),
                                    dbc.Button(
                                        id="reset-file-btn",
                                        className="btn btn-outline",
                                        title="Purge cache",
                                        children=DashIconify(icon="qlementine-icons:reset-16"),
                                    ),
                                    dbc.Button(
                                        id="download-file-btn",
                                        title="Download",
                                        children=DashIconify(icon="bi:download")
                                    ),
                                    dcc.Download(id="file-download"),
                                    dbc.Button(
                                        id="rename-file-btn",
                                        title="Rename",
                                        children=DashIconify(icon="ic:outline-drive-file-rename-outline")
                                    ),
                                    dbc.Button(
                                        id="open-file-btn",
                                        title="Open",
                                        children=DashIconify(icon="majesticons:open-line"),
                                    ),
                                ),
                            )
                        )
                    ),
                    # TODO remove example
                    # html.Button(
                    #     id="tab-example",
                    #     children="Tab example",
                    # ),
                ),
            ),

            # html.Div(
            #     id="workspace-context-menu",
            #     className="dropdown position-absolute",
            #     style={"display":"none", "zIndex": "-1"},
            #     role="menu",
            #     children=html.Ul(
            #         className="dropdown-menu",
            #         children=html.Li("Test")
            #     )
            # ),
            # html.Div(
            #     id="workspace-context-menu-overlay",
            #     className="position-absolute bg-dark",
            #     style={"display":"none", "zIndex": "-1"}
            # )
            dmc.Modal(
                title="Rename file",
                id="rename-modal",
                centered=True,
                zIndex=10000,
                children=(
                    dbc.InputGroup(
                        children=(
                            dbc.InputGroupText(
                                id="rename-modal-input-file-type",
                            ),
                            dbc.Input(
                                id="rename-modal-input",
                            ),
                            dbc.InputGroupText(
                                id="rename-modal-input-naming-convention",
                            )
                        )
                    ),
                    dbc.Button(
                        id="rename-modal-confirm",
                        className="float-end my-3",
                        children="Confirm"
                    )
                )
            ),
        )
     )
    
def render_default_workspace_summary_content():
    return html.Div(
        className="d-flex flex-column",
        children=(
            html.H6("Click on any file to see its summary here"),
            html.Img(
                src="static/placeholder.png",
                className="opacity-25"
            )
        )
    )

@callback(
    Output("left-sidebar", "className"),
    Output("content", "width"),
    Output("collapse-btn", "children"),
    Input("collapse-btn", "n_clicks"),
    State("content", "width"),
    prevent_initial_call=True
)
def collapse_sidebar(_, state):
    if state == 10:
        return left_sidebar_class_name + " position-absolute d-none", 12, DashIconify(icon="material-symbols:chevron-right")
    else:
        return left_sidebar_class_name, 10, DashIconify(icon="material-symbols:chevron-left")

def render_file_summary(summary, path):
    if summary is None:
        summary_table = html.Tr(html.Th("Unsupported file type"))
    else:
        summary_table = [
            html.Tr(
                children=(
                    html.Th(k),
                    html.Td(summary[k])
                )
            ) for k in summary.keys()
        ]
    return html.Table(
        id=make_id(path, type="summary-table"),
        children=html.Tbody(children=summary_table)
    )

def init_usr_file():
    wd = g.user_data["wd"]
    # return [dbc.ListGroupItem(i) for i in os.listdir(wd)]
    # HACK use a sec interval to update workspace, because callback of dash_uploader doesnt work for some reason
    return FileTree(wd).render(), dcc.Interval(
        id="workspace-forever-interval",
        interval=2000
    ), dcc.Store(id="workspace-last-update-store", clear_data=True, data=time())

@callback(
    Output("workspace-file-list", "children", allow_duplicate=True),
    Output("workspace-last-update-store", "data"),
    Input("workspace-forever-interval", "n_intervals"),
    State("workspace-last-update-store", "data"),
    prevent_initial_call=True
)
def update_workspace(_, last_update):
    wd = g.user_data["wd"]
    if last_update is None or os.path.getmtime(wd) > last_update:
        file_list = Patch()
        file_list[0] = FileTree(wd).render()
        return file_list, time()
    return no_update, no_update

left_sidebar_init_targets = (
    ("workspace-file-list", "children", init_usr_file),
)


@callback(
    Output("workspace-file-summary-content", "children", allow_duplicate=True),
    Output("file-controls", "className", allow_duplicate=True),
    Output("open-file-btn", "disabled"),
    Input(make_generic_id(ALL, type="workspace-file-item"), "n_clicks"),
    running=(
        (Output("workspace-summary-loading", "display"), "show", "hide"),
    ),
    prevent_initial_call=True
)
def get_file_summary(_):
    if len(_) == 0: return no_update
    if not any(_): return no_update

    try:
        summary = read_summary_and_cache_file(decode_path(ctx.triggered_id))
        can_open = True
    except:
        print(traceback.format_exc())
        summary = None
        can_open = False
    return render_file_summary(summary, decode_path(ctx.triggered_id)), "d-flex", not can_open

@callback(
    Output("content-tabs", "children", allow_duplicate=True),
    Output("content-tabs", "value", allow_duplicate=True),
    Input("open-file-btn", "n_clicks"),
    State(make_generic_id(ALL, type="summary-table"), "id"),
    State({"type": "content-tab-list", "index": ALL}, "value"),
    # running=(
    #     (Output("content-loading", "display"), "show", "hide"),
    # ),
    prevent_initial_call=True
)
def open_file(_, table_id, tab_values):
    if not bool(_): return no_update
    
    path = decode_path(table_id[0])
    
    if path in tab_values:
        return no_update
    
    file = read_check_and_cache_file(path)
    if file.item_type == FileType.RAW:
        new_tab = render_raw_content(file)
        # tab = render_raw_content(file.item, path=path)
    elif file.item_type == FileType.EPOCH:
        new_tab = render_epoch_content(file)
    elif file.item_type == FileType.EVOKED:
        new_tab = render_evoked_content(file)
    elif file.item_type == FileType.ESI:
        new_tab = render_esi_content(file.item, path=path)
    else:
        raise ValueError("This shouldn't be possible")

    return append_to_tabs(tab_values, *new_tab)

# @callback(
#     Output("content-tabs", "value"),
#     Input("open-file-btn", "n_clicks"),
#     State(make_generic_id(ALL, type="summary-table"), "id"),
#     State(make_generic_id(ALL, type="content-tab-list"), "value"),
#     prevent_initial_call=True
# )
# def swap_tab(_, table_id, tab_values):
    # FIXME current design of tabs broke this
    # path = decode_path(table_id[0])
    
    # if bool(_) and path in tab_values:
    #     return path
    # return no_update

@callback(
    Output("file-download", "data"),
    Input("download-file-btn", "n_clicks"),
    State(make_generic_id(ALL, type="summary-table"), "id"),
    prevent_initial_call=True
) # FIXME probably inefficient when downloading large file but I am not dealing with that now
def download_file(_, id):
    # print("download")
    if not _:
        return no_update
    path = decode_path(id[0])
    validate_access(path)
    return dcc.send_file(path)


@callback(
    Output("notifications-container", "children", allow_duplicate=True),
    Output("workspace-file-summary-content", "children", allow_duplicate=True),
    Output("file-controls", "className", allow_duplicate=True),
    Input("delete-file-btn", "n_clicks"),
    State(make_generic_id(ALL, type="summary-table"), "id"),
    prevent_initial_call=True
)
def delete_file(_, id):
    # print("delete")
    if not _:
        return no_update
    path = decode_path(id[0])
    validate_access(path)
    # print("delete")
    # print(path)
    
    # NOTE if exception occur, and notification is one of the Output, previous notification will be replayed
    try:
        os.remove(path)
        notif = dmc.Notification(
            title="File deleted!",
            action="show",
            message=f"File {path[len(g.user_data['wd']) + 1:]} has been deleted",
            icon=DashIconify(icon="ep:success-filled", color="chartreuse", width=30)
        )
        workspace_summary = render_default_workspace_summary_content()
        file_control_class = "d-none"
    except:
        print(traceback.format_exc())
        notif = dmc.Notification(
            title="Failed to delete file",
            action="show",
            message=f"Failed to delete file {path[len(g.user_data['wd']) +  1:]}",
            icon=DashIconify(icon="ep:circle-close-filled", color="red", width=30)
        )
        workspace_summary = no_update
        file_control_class = no_update
    return notif, workspace_summary, file_control_class


@callback(
    Output("rename-modal", "opened", allow_duplicate=True),
    Output("rename-modal-input", "placeholder"),
    Output("rename-modal-input", "value"),
    Output("rename-modal-input-naming-convention", "children"),
    Output("rename-modal-input-file-type", "children"),
    Input("rename-file-btn", "n_clicks"),
    State("rename-modal", "opened"),
    State(make_generic_id(ALL, type="summary-table"), "id"),
    prevent_initial_call=True,
)
def toggle_modal(_, opened, id):
    path = decode_path(id[0])
    file_type = infer_file_type(path)
    
    name, ext = os.path.splitext(os.path.basename(path))
    if file_type == FileType.EPOCH:
        convention = "-epo.fif"
        name = name[:-4]
    elif file_type == FileType.EVOKED:
        convention = "-ave.fif"
        name = name[:-4]
    else:
        convention = ext

    return not opened, name, None, convention, FileTree.get_file_icon(file_type)

@callback(
    Output("rename-modal", "opened", allow_duplicate=True),
    Output("notifications-container", "children", allow_duplicate=True),
    Input("rename-modal-confirm", "n_clicks"),
    State("rename-modal-input", "value"),
    State(make_generic_id(ALL, type="summary-table"), "id"),
    State("rename-modal-input-naming-convention", "children"),
    prevent_initial_call=True
)
def perform_rename(_, new_name, id, convention):
    path = decode_path(id[0])
    parent = path[:-len(os.path.basename(path))]
    new_path = parent + new_name + convention
    validate_access(path)
    validate_access(new_path)
    # print("rename")
    # print(path)
    # print(new_path)
    # NOTE if exception occur, and notification is one of the Output, previous notification will be replayed
    try:
        os.rename(path, new_path)
        notif = dmc.Notification(
            title="File renamed!",
            action="show",
            message=f"File {path[len(g.user_data['wd']) +  1:]} has been renamed to {new_name}{convention}",
            icon=DashIconify(icon="ep:success-filled", color="chartreuse", width=30)
        )
    except:
        print(traceback.format_exc())
        notif = dmc.Notification(
            title="Failed to rename file",
            action="show",
            message=f"Failed to rename file {path[len(g.user_data['wd']) +  1:]}",
            icon=DashIconify(icon="ep:circle-close-filled", color="red", width=30)
        )
    return False, notif

# @callback(
#     Output("notifications-container", "children", allow_duplicate=True),
#     Input("test-btn", "n_clicks"),
#     prevent_initial_call=True
# )
# def test(_):
#     # print("download")
#     if _ % 2 == 0:
#         return no_update
#     raise ""

@callback(
    Output("notifications-container", "children", allow_duplicate=True),
    Input("reset-file-btn", "n_clicks"),
    State(make_generic_id(ALL, type="summary-table"), "id"),
    prevent_initial_call=True
)
def purge_file_cache(_, id):
    # print("download")
    if not _:
        return no_update
    path = decode_path(id[0])
    # validate_access(path)
    # TODO validate access once is enough

    # NOTE if exception occur, and notification is one of the Output, previous notification will be replayed
    try:
        remove_cache(path)
        notif = dmc.Notification(
            title="File reset!",
            action="show",
            message=f"Cache of file {path[len(g.user_data['wd']) +  1:]} has been removed",
            icon=DashIconify(icon="ep:success-filled", color="chartreuse", width=30)
        )
    except:
        print(traceback.format_exc())
        notif = dmc.Notification(
            title="Failed to reset file",
            action="show",
            message=f"Failed to reset file {path[len(g.user_data['wd']) +  1:]}",
            icon=DashIconify(icon="ep:circle-close-filled", color="red", width=30)
        )
    return notif

###################################################################################
# https://community.plotly.com/t/file-explorer-tree-generator-for-local-files/68732
class FileTree:
    file_className = None

    def __init__(self, filepath: os.PathLike):
        """
        Usage: component = FileTree('Path/to/my/File').render()
        """
        self.filepath = filepath

    def render(self):
        return dmc.Accordion(
            self.build_tree(self.filepath, isRoot=True), multiple=True)

    def flatten(self, l):
        return [item for sublist in l for item in sublist]

    def make_file(self, path):
        return dmc.NavLink(
            label=[self.get_file_icon(infer_file_type(path)), " ", os.path.basename(path)], style={"paddingTop": '5px'},
            id=make_id(path, type="workspace-file-item"),
            className=FileTree.file_className,
        )

    def make_folder(self, folder_name):
        return [DashIconify(icon="akar-icons:folder", width=20), " ", folder_name]

    def build_tree(self, path, isRoot=False):
        d = []
        if os.path.isdir(path):
            if os.path.basename(path) == _CACHE_DIR:
                return []
            children = self.flatten([self.build_tree(os.path.join(path, x))
                                    for x in os.listdir(path)])
            if isRoot:
                d.append(
                    dmc.AccordionItem([
                        dmc.AccordionControl(self.make_folder(os.path.basename(path))),
                        dmc.AccordionPanel(children=children)
                        ], value=str(path))
                )
            else:
                d.append(
                    dmc.Accordion(children=[
                        dmc.AccordionItem([
                            dmc.AccordionControl(self.make_folder(os.path.basename(path))),
                            dmc.AccordionPanel(children=children)
                            ], value=str(path))
                    ], multiple=True)
                )
        else:
            d.append(self.make_file(path))
        return d
    @staticmethod
    def get_file_icon(type):
        return DashIconify(
            icon={
                FileType.UNSUPPORTED:"carbon:document-unknown",
                FileType.RAW: "bi:filetype-raw",
                FileType.EPOCH: "gg:stack",
                FileType.EVOKED: "f7:waveform-path-ecg",
                FileType.ESI: "gis:location-on",
            }[type],
            width=20
        )
