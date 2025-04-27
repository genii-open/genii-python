from flask import g, abort
import os

def make_id(path, **kwargs):    
    real_path = os.path.realpath(path)
    real_wd = os.path.realpath(g.user_data["wd"])
    
    if os.path.commonprefix((real_path, real_wd)) != real_wd:
        abort(401)
    # TODO prevent exposing wd?
    # path = real_path[len(real_wd):]

    pth, ext = os.path.splitext(path)
    return {"pth": pth, "ext": ext[1:], **kwargs}

def make_generic_id(mode, **kwargs):
    return {"pth": mode, "ext": mode, **kwargs}

def decode_path(id):
    return id["pth"] + "." + id["ext"]