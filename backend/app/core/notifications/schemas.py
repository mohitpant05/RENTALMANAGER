import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    event_type: str
    title: str
    body: str
    payload: dict | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def message(self) -> str:
        return self.body or self.title


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    marked: int
