from enum import IntEnum
from typing import NotRequired, TypedDict
import os

IPC_NAME = "yomu-ipc-dev" if int(os.getenv("YOMU_DEV", "0")) else "yomu-ipc"


class Command(IntEnum):
    UNKNOWN, SHOW, NEW_WINDOW, OPEN_SOURCE = range(-1, 3)

    @classmethod
    def from_code(cls, code: int) -> Command:
        try:
            return cls(code)
        except ValueError:
            return cls.UNKNOWN


class RequestData(TypedDict):
    cmd: Command


class SourceRequestData(RequestData):
    name: str
    winId: int


class ReturnData(TypedDict):
    success: bool
    reason: NotRequired[str]


class WindowReturnData(ReturnData):
    winId: int
