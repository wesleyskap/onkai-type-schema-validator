from datetime import datetime
import pytest
from typed_schema_validator import Schema, dump, field_serializer, validate


class Event(Schema, frozen=True):
    title: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(cls, v: datetime) -> str:
        return v.strftime("%Y-%m-%d %H:%M:%S")


def test_schema_copy_mutable_and_frozen():
    dt = datetime(2025, 10, 20, 14, 30, 0)
    event = validate(Event, {"title": "Original Event", "created_at": dt})

    # Copy frozen schema with updates
    copied_event = event.copy(update={"title": "Updated Event"})

    assert isinstance(copied_event, Event)
    assert copied_event.title == "Updated Event"
    assert copied_event.created_at == dt
    assert event.title == "Original Event"  # Original unchanged


def test_custom_field_serializer():
    dt = datetime(2025, 10, 20, 14, 30, 0)
    event = Event(title="Conference", created_at=dt)

    serialized = dump(event)
    assert serialized == {
        "title": "Conference",
        "created_at": "2025-10-20 14:30:00",
    }
