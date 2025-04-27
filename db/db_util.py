import os
import uuid
import string
import hashlib
from .data_structure import UserData


import sqlite3

# TODO persistant database & service
con = sqlite3.connect(":memory:", check_same_thread=False)
con.cursor().execute("" \
    "CREATE TABLE user (" \
        "id INTEGER PRIMARY KEY NOT NULL," \
        "name TEXT NOT NULL," \
        "email TEXT NOT NULL UNIQUE," \
        "pwd BLOB NOT NULL," \
        "token TEXT NULL" \
    ");"
)
con.cursor().execute("" \
    "INSERT into user(id, name, email, pwd, token) values(?, ?, ?, ?, ?)", (
        # uuid.uuid4(),
        0,
        "Puah Jia Hong",
        "meg2311003@xmu.edu.my",
        b'\xc2\xc1:\xe2\xef\xca\xdc\xb4`\xebDF\xc4\x18=\x86\xb5\x7f\xc0\xa1,M\x9f\xf5\xce\xba|WH\xd7\xdb\xe5',
        None
    ))
con.commit()

def _get_user_by_email(email):
    global con
    cursor = con.cursor()
    try:
        cursor.execute("SELECT * FROM user WHERE user.email = ?", (email,))
        return UserData(*cursor.fetchone())
    except:
        return None

def _get_user_by_token(token):
    global con
    cursor = con.cursor()
    try:
        cursor.execute("SELECT * FROM user WHERE user.token = ?", (token,))
        return UserData(*cursor.fetchone())
    except:
        return None

def _set_user_token(id, token):
    global con
    cursor = con.cursor()
    try:
        cursor.execute("UPDATE user SET token = ? WHERE id = ?", (token, id))
        con.commit()
        return True
    except:
        return False


def _delete_user_token(id):
    global con
    cursor = con.cursor()
    try:
        cursor.execute("UPDATE user SET token = NULL WHERE id = ?", (id,))
        con.commit()
        return True
    except:
        return False

def user_login(email, pwd):
    usr_data = _get_user_by_email(email)
    if usr_data is None or hashlib.sha256(pwd.encode("utf-8")).digest() != usr_data["pwd"]:
        return None
    usr_data["token"] = str(uuid.uuid4())
    _set_user_token(usr_data.id, usr_data.token)
    return usr_data["token"]

def get_user_detail_wih_token(token):
    usr_data = _get_user_by_token(token)
    if usr_data is not None:
        usr_data.wd = get_user_working_directory(usr_data.id)
        return usr_data
    return None

def get_user_working_directory(id):
    # TODO load from database of sth
    path = os.path.join("uploaded_files", str(id))
    if not os.path.exists(path):
        os.mkdir(path)
    return path

def user_logout(user_id):
    _delete_user_token(user_id)