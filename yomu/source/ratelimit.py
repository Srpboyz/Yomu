from yomu.core.network.ratelimit import *


def warn():
    from warnings import warn

    warn(
        "yomu.source.ratelimit is deprecated and will be removed in version 1.4. Use yomu.core.network.ratelimit",
        category=DeprecationWarning,
        stacklevel=2,
    )


warn()
del warn
