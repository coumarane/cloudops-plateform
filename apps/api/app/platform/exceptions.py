class PlatformError(Exception):
    pass


class PlatformNotFoundError(PlatformError):
    pass


class PlatformConflictError(PlatformError):
    pass


class PlatformStateError(PlatformError):
    pass
