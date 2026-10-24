from datetime import datetime
from pydantic import BaseModel


class Student(BaseModel):
  student_id: int
  matrikel: str
  vorname: str
  nachname: str
  programme: str
  semester: int


class StudentCreate(BaseModel):
  matrikel: str
  vorname: str
  nachname: str
  programme: str
  semester: int


class StudentUpdate(BaseModel):
  matrikel: str
  vorname: str
  nachname: str
  programme: str
  semester: int


class Module(BaseModel):
  module_id: int
  name: str


class ModuleCreate(BaseModel):
  name: str


class Grade(BaseModel):
  grade_id: int
  student_id: int
  module_id: int
  grade_value: str
  graded_at: datetime


class GradeCreate(BaseModel):
  student_id: int
  module_id: int
  grade_value: str
