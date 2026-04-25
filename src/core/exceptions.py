"""Domain exceptions for the liquid-handler package."""


class LHError(Exception):
    """Base exception for liquid-handler domain failures."""


class ConfigurationError(LHError):
    """Raised when configuration data is missing or invalid."""


class MoonrakerError(LHError):
    """Raised when a Moonraker RPC or connection operation fails."""


class MotionError(LHError):
    """Raised when motion planning or motion status checks fail."""


class PipetteError(LHError):
    """Raised when a pipette command is outside the configured range."""
