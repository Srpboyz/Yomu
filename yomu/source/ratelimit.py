from dataclasses import dataclass
from enum import IntEnum
from numbers import Real

__all__ = ("RateLimit", "TimeUnit")


class TimeUnit(IntEnum):
    HOURS, MINUTES, SECONDS, MILLISECONDS = range(4)


@dataclass(frozen=True, repr=False, slots=True)
class RateLimit:
    rate: int
    per: Real = 1
    unit: TimeUnit = TimeUnit.SECONDS

    def __post_init__(self):
        if not isinstance(self.rate, int):
            raise TypeError("rate must be an int")
        if not isinstance(self.per, Real):
            raise TypeError("per must be a number")
        if not isinstance(self.unit, TimeUnit):
            raise TypeError("unit must be a TimeUnit enum")

    @property
    def milliseconds(self) -> float:
        match self.unit:
            case TimeUnit.HOURS:
                return self.per * 60 * 60 * 1000
            case TimeUnit.MINUTES:
                return self.per * 60 * 1000
            case TimeUnit.SECONDS:
                return self.per * 1000
            case TimeUnit.MILLISECONDS:
                return self.per

    def __repr__(self) -> str:
        return f"<RateLimit rate={self.rate} per={self.per} unit={self.unit.name}>"
