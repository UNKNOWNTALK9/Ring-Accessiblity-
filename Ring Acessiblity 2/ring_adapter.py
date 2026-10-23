# =====================================================================
# Adapter boundary for an approved Ring API/SDK or hackathon simulator.
# =====================================================================
from typing import Iterable, Protocol, TypedDict

class RingEvent(TypedDict, total=False):
    event_id: str
    event_type: str
    device_name: str
    description: str

class RingAdapter(Protocol):
    def connect(self) -> bool: ...
    def events(self) -> Iterable[RingEvent]: ...
    def close(self) -> None: ...

class LiveAdapterNotConfigured(RuntimeError):
    pass

def create_adapter() -> RingAdapter:
    raise LiveAdapterNotConfigured(
        "No approved Ring adapter configured. Implement this module only after "
        "confirming the hackathon's documented API/SDK and permissions."
    )
