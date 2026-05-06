from enum import Enum

class WidgetType(Enum):
    CENTRAL = 0,
    BUTTONS = 1

class EditMode(Enum):
    DROPDOWN = 0,
    TEXT = 1,
    RADIO = 2