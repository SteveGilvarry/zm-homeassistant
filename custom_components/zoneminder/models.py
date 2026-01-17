"""Data models for the ZoneMinder integration."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Monitor:
    """Representation of a ZoneMinder monitor."""

    id: int
    name: str
    function: str
    enabled: bool
    width: int
    height: int
    type: str  # Local, Remote, Ffmpeg, etc.
    protocol: str | None = None
    host: str | None = None
    path: str | None = None
    port: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Monitor":
        """Create Monitor from API response."""
        monitor_data = data.get("Monitor", data)
        return cls(
            id=int(monitor_data["Id"]),
            name=monitor_data["Name"],
            function=monitor_data["Function"],
            enabled=bool(int(monitor_data["Enabled"])),
            width=int(monitor_data["Width"]),
            height=int(monitor_data["Height"]),
            type=monitor_data["Type"],
            protocol=monitor_data.get("Protocol"),
            host=monitor_data.get("Host"),
            path=monitor_data.get("Path"),
            port=int(monitor_data["Port"]) if monitor_data.get("Port") else None,
        )


@dataclass
class Event:
    """Representation of a ZoneMinder event."""

    id: int
    monitor_id: int
    name: str
    cause: str
    start_time: datetime
    end_time: datetime | None
    length: float  # Duration in seconds
    frames: int
    alarm_frames: int
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """Create Event from API response."""
        event_data = data.get("Event", data)

        # Parse timestamps
        start_time = datetime.fromisoformat(
            event_data["StartTime"].replace(" ", "T")
        )
        end_time = None
        if event_data.get("EndTime"):
            try:
                end_time = datetime.fromisoformat(
                    event_data["EndTime"].replace(" ", "T")
                )
            except (ValueError, AttributeError):
                pass

        return cls(
            id=int(event_data["Id"]),
            monitor_id=int(event_data["MonitorId"]),
            name=event_data["Name"],
            cause=event_data["Cause"],
            start_time=start_time,
            end_time=end_time,
            length=float(event_data.get("Length", 0)),
            frames=int(event_data.get("Frames", 0)),
            alarm_frames=int(event_data.get("AlarmFrames", 0)),
            notes=event_data.get("Notes"),
        )

    @property
    def is_active(self) -> bool:
        """Return True if event is currently active (no end time)."""
        return self.end_time is None


@dataclass
class MonitorData:
    """Combined monitor and event data for coordinator."""

    monitor: Monitor
    latest_event: Event | None = None
