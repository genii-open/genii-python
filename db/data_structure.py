from dataclasses import dataclass
from enum import Enum
from typing import Any

class FileType(Enum):
    RAW=0
    EPOCH=1
    EVOKED=2
    ESI=3
    UNSUPPORTED=-1

@dataclass
class File():
    item: Any
    item_type: FileType
    dirty: bool
    path: str

@dataclass
class UserData(dict):
    id: int
    name: str
    email: str
    pwd: str
    token: str
    wd: str

    # FIXME ?????
    def __init__(self, id, name, email, pwd, token):
        self.id=id
        self.name=name
        self.email=email
        self.pwd=pwd
        self.token=token

    def __getitem__(self, key):
        return self.__getattribute__(key)
    
    def __setitem__(self, key, value):
        self.__setattr__(key, value)
    