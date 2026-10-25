from datetime import datetime
from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    serial_number: str = Field(..., min_length=1, examples=["SN-LAP-003"])
    device_type_id: int = Field(..., examples=[1])
    location_id: int = Field(..., examples=[1])
    note: str | None = Field(default=None, examples=["ThinkPad X1 Carbon"])


class DeviceUpdate(BaseModel):
    serial_number: str = Field(..., min_length=1, examples=["SN-LAP-003"])
    device_type_id: int = Field(..., examples=[1])
    location_id: int = Field(..., examples=[1])
    note: str | None = Field(default=None, examples=["ThinkPad X1 Carbon"])


class DeviceOut(BaseModel):
    device_id: int
    serial_number: str
    device_type_id: int
    device_type_name: str
    location_id: int
    location_name: str
    note: str | None = None
    status: str


class AssignmentCreate(BaseModel):
    device_id: int = Field(..., examples=[3])
    person_id: int = Field(..., examples=[1])
    issued_at: str | None = Field(default=None, examples=["2026-10-24T12:00:00+02:00"])


class AssignmentReturn(BaseModel):
    returned_at: str | None = Field(default=None, examples=["2026-10-24T14:00:00+02:00"])


class AssignmentOut(BaseModel):
    assignment_id: int
    device_id: int
    serial_number: str
    device_type_name: str
    person_id: int
    person_name: str
    issued_at: datetime
    returned_at: datetime | None = None


