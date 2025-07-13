from dataclasses import dataclass, field
from enum import IntEnum

__all__ = ("RateLimit", "TimeUnit")


class TimeUnit(IntEnum):
    HOURS, MINUTES, SECONDS, MILLISECONDS = range(4)


@dataclass(frozen=True, repr=False, slots=True)
class RateLimit:
    rate: int
    per: float
    unit: TimeUnit = field(default=TimeUnit.SECONDS)

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
