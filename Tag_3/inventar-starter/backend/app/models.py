from pydantic import BaseModel


# Hinweis:
# Diese Modelle sind nur ein möglicher Startpunkt für die Übung.
# Ihr dürft Felder ergänzen, umbenennen oder weitere Modelle anlegen.


class DeviceCreate(BaseModel):
  serial_number: str
  device_type_id: int
  location_id: int
  note: str | None = None


class AssignmentCreate(BaseModel):
  device_id: int
  person_id: int
  issued_at: str | None = None


class AssignmentReturn(BaseModel):
  returned_at: str | None = None

