from enum import Enum


class Depot(str, Enum):
    NSW = "NSW"
    VIC = "VIC"


class ContainerType(str, Enum):
    STD_20 = "20STD"
    STD_40 = "40STD"
    SDL_20 = "20SDL"
    SDL_40 = "40SDL"
    DROP_20 = "20DROP"
    DROP_40 = "40DROP"


class DeliverType(str, Enum):
    IMPORT = "Import"
    EXPORT = "Export"
    EMPTY = "Empty"


class LogisticsStatus(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class TerminalName(str, Enum):
    DP_WORLD_NSW = "DP World NSW"
    DP_WORLD_VIC = "DP World VIC"
    PATRICK_NSW = "Patrick NSW"
    PATRICK_VIC = "Patrick VIC"
    HUTCHISON_NSW = "Hutchison NSW"
    VICT_VIC = "VICT VIC"
