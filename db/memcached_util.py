from dataclasses import dataclass
from typing import Tuple
from .data_structure import File
import os
from flask import g, abort
import mne

# HACK current strategy: make a copy of original file instead of proper caching
_CACHE_DIR = "__NEUROII_CACHE"

# In development env without memcached running, fallback to sqlite3 in memory database
# try:
#     import pymemcache
#     client = pymemcache.Client('localhost:11211', serde=pymemcache.serde.pickle_serde)
#     client.set("online", True)

# except:
#     import sqlite3
#     import pickle
#     class Client():
#         def __init__(self):
#             print("WARNING: Memcached not setup. Using Sqlite3 as fallback, this is not thread-safe, not memory efficient and should not be used in production")
#             # HACK This is not thread safe, do not use in production
#             self.con = sqlite3.connect(":memory:", check_same_thread=False)
#             self.con.cursor().execute("CREATE TABLE cache_table (key TEXT PRIMARY KEY, val BLOB);")
#         def get(self, key, default=None, **kwargs):
#             cur = self.con.cursor()
#             query = "SELECT val FROM cache_table where key = ?"
#             cur.execute(query, (key, ))
#             try:
#                 return pickle.loads(cur.fetchone()[0])
#             except:
#                 return default
            
#         def set(self, key, val, **kwargs):
#             cur = self.con.cursor()
#             b = pickle.dumps(val)
#             if self.get(key) is not None:
#                 query = "UPDATE cache_table SET val = ? WHERE key = ?"
#                 params = (b, key)
#             else:
#                 query = "INSERT INTO cache_table(key, val) values(?, ?)"
#                 params = (key, b)
#             cur.execute(query, params)

#     client = Client()

# FIXME duplicated function
def validate_access(path):
    real_path = os.path.realpath(path)
    real_wd = os.path.realpath(g.user_data["wd"])
    
    if os.path.commonprefix((real_path, real_wd)) != real_wd:
        # FIXME weird abort bug
        # abort(401)
        pass

def get_cached_item(key, default=None) -> File:
    # HACK
    validate_access(key)

    cached_item_path = os.path.join(
        g.user_data["wd"],
        _CACHE_DIR,
        _generate_cached_item_name(os.path.basename(key))
    )

    if os.path.exists(cached_item_path) and os.path.isfile(cached_item_path):
        from file_io import _open_file_without_caching
        return _open_file_without_caching(cached_item_path)
    return default
    # return client.get(key, default)

def set_cache_item(key, val: File, expire=0):
    # HACK
    # check cache dir exist
    cache_dir = os.path.join(g.user_data["wd"], _CACHE_DIR)
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)
    
    # make a copy to cache dir with generated name
    cached_item_path = os.path.join(
        g.user_data["wd"],
        _CACHE_DIR,
        _generate_cached_item_name(os.path.basename(key))
    )
    
    from file_io import save_mne_object
    save_mne_object(val.item, cached_item_path)

    # register cache existance?

    # client.set(key, val, expire=expire)

def get_cached_files(token) -> Tuple[File, ...]:
    return tuple()
    # return client.get(token)

def _generate_cached_item_name(basename):
    #TODO
    return basename

def remove_cache(key):
    validate_access(key)
    
    cached_item_path = os.path.join(
        g.user_data["wd"],
        _CACHE_DIR,
        _generate_cached_item_name(os.path.basename(key))
    )
    if os.path.exists(cached_item_path) and os.path.isfile(cached_item_path):
        os.remove(cached_item_path)
        return True
    return False