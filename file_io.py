import os
from db.memcached_util import get_cached_item, set_cache_item
from compumedics_util import Compumedics
import mne
from flask import g, abort
from enum import Enum
from db.data_structure import File, FileType

expire = 3 * 60 * 60 # 3 hours

class _DetailedFileType(Enum):
    COMPUMEDICS = 1
    NICOLET = 2
    MISC_RAW = 3
    MNE_EPOCH = 4
    MNE_EVOKED = 5
    MNE_ESI = 6
    UNSUPPORTED = -1

# 读取文件，并检查其文件类型（raw, epoch, ...）
def read_check_and_cache_file(path):
    validate_access(path)
    
    cache_item = get_cached_item(path)
    # print(cache_item)
    if cache_item is not None:
        return cache_item

    item = _open_file_without_caching(path)
    
    set_cache_item(path, item)
    return item

def read_summary_and_cache_file(path):
    file = read_check_and_cache_file(path)
    file_type = file.item_type

    info = {}
    for k in file.item.info.keys():
        if k in ("nchan", "sfreq", "bads", 
                #  "description", 
                 "highpass", "lowpass", 
                #  "meas_date"
                 ):
            info[k] = file.item.info[k]
    
    if file_type == FileType.RAW:
        info["type"] = "Raw"
        info["n_times"] = file.item.n_times
    elif file_type == FileType.EPOCH:
        info["type"] = "Epoch"
        info["tmin"] = file.item.tmin
        info["tmax"] = file.item.tmax
        # TODO Event related info
    elif file_type == FileType.EVOKED:
        info["type"] = "Evoked"
        info["nave"] = file.item.nave
        info["tmin"] = file.item.tmin
        info["tmax"] = file.item.tmax
        # TODO Event related info
    return info
    # TODO
    # info = {}

    # for k in file.item.info.keys():
    #     if k in ("bads", "ch_names", "description", "highpass", "lowpass", "meas_date", "nchan", "sfreq", "subject_info"):
    #         info[k] = file.item.info[k]
    
    # # TODO projection
    # info["time_point"] = 


    # elif file_type == FileType.RAW:
    #     info["type"] = "Compumedic"
    # elif False: #TODO Nicolet
    #     info["type"] = "Nicolet"
    # return info

# 只读取文件
def read_and_cache_file(path):
    return read_check_and_cache_file(path).item

# 将物件储存进cache里
# TODO security check & security when cache miss
def cache_file(obj, type: FileType, dirty: bool, path: str):
    file = File(
        obj, type, dirty, path
    )
    set_cache_item(
        path,
        file,
        expire
    )
    return file

def get_appropriate_ext(item_type: FileType):
    if item_type == FileType.RAW:
        return ".fif"
    if item_type == FileType.EPOCH:
        return "-epo.fif"
    if item_type == FileType.EVOKED:
        return "-ave.fif"
    return ""

# 储存文件
def save_mne_object(obj, path: str):
    validate_access(path)
    obj.save(path, overwrite=True) # MNE objects

def _infer_file_type(path):
    if path[-4:] in (".eeg", ".sdy", ".rda"): # Compumedic
        return _DetailedFileType.COMPUMEDICS
    elif path[-2:] == ".e": # TODO Nicolet support
        return _DetailedFileType.NICOLET
    elif path[-8:] == "-ave.fif": # MNE Evoked array
        return _DetailedFileType.MNE_EVOKED
    elif path[-8:] == "-epo.fif": # MNE Epochs
        return _DetailedFileType.MNE_EPOCH
    # HACK copied from mne.io._read_raw
    elif path[-7:] == "-vl.stc":
        return _DetailedFileType.MNE_ESI
    elif os.path.splitext(path)[1] in (
        ".edf",
        ".eeg",
        ".bdf",
        ".gdf",
        ".vhdr",
        ".ahdr",
        ".fif",
        ".fif.gz",
        ".set",
        ".cnt",
        ".mff",
        ".nxe",
        ".hdr",
        ".snirf",
        ".mat",
        ".bin", 
        ".data",
        ".sqd",
        ".con",
        ".ds",
        ".txt",
        ".dat",
        ".dap",
        ".rs3",
        ".cdt",
        ".cdt.dpa",
        ".cdt.cef",
        ".cef",
        ".nedf",
        ".vmrk",
        ".amrk",
    ):
        return _DetailedFileType.MISC_RAW 
    else:
        return _DetailedFileType.UNSUPPORTED
    # TODO ESI

def infer_file_type(path):
    # TODO remember to update this when supporting more file
    return {
        _DetailedFileType.COMPUMEDICS: FileType.RAW,
        _DetailedFileType.NICOLET: FileType.UNSUPPORTED,
        _DetailedFileType.MNE_EVOKED: FileType.EVOKED,
        _DetailedFileType.MNE_EPOCH: FileType.EPOCH,
        _DetailedFileType.MISC_RAW:FileType.RAW,
        _DetailedFileType.UNSUPPORTED: FileType.UNSUPPORTED,
        _DetailedFileType.MNE_ESI: FileType.UNSUPPORTED,
    }[_infer_file_type(path)]

def validate_access(path):
    real_path = os.path.realpath(path)
    real_wd = os.path.realpath(g.user_data["wd"])
    
    if os.path.commonprefix((real_path, real_wd)) != real_wd:
        #FIXME weird abort bug
        #abort(401)
        pass

def _open_file_without_caching(path):
    file_type = _infer_file_type(path)

    if file_type == _DetailedFileType.COMPUMEDICS:
        item = File(
            Compumedics(path).export_to_mne_raw(),
            FileType.RAW,
            False,
            path
        )
    elif file_type == _DetailedFileType.NICOLET:
        raise NotImplementedError("Support for Nicolet file is not implemented yet")
    elif file_type == _DetailedFileType.MNE_EVOKED:
        item = File(
            mne.read_evokeds(path, condition=0),# FIXME potentially support for multiple evked in one file?
            FileType.EVOKED,
            False,
            path
        )
    elif file_type == _DetailedFileType.MNE_EPOCH:
        item = File(
            mne.read_epochs(path),
            FileType.EPOCH,
            False,
            path
        )
    elif file_type == _DetailedFileType.MISC_RAW:
        item = File(
            mne.io.read_raw(path, preload=True), # FIXME potentially use a lot of RAM
            FileType.RAW,
            False,
            path
        )
    # raise here is very pointless
    elif file_type == _DetailedFileType.MNE_ESI:
        item = File(
            mne.read_source_estimate(path),
            FileType.ESI,
            False,
            path
        )
        # raise NotImplementedError("Support of ESI is yet to be implemented")
    elif file_type == _DetailedFileType.UNSUPPORTED:
        raise ValueError("Unsupported file type")
    return item