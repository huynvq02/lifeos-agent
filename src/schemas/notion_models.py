from pydantic import BaseModel, Field
from datetime import datetime

class Area(BaseModel):
    id: str
    name: str
    description: str

class Project(BaseModel):
    id: str
    name: str
    area: str = Field(description="E.g., Health, Work, Personal")
    status: str = Field(description="E.g., On hold, Active, Done")
    start_date: datetime = Field(description="Start date")
    end_date: datetime = Field(description="End date")
    description: str = Field(description="Description of the project")

class Task(BaseModel):
    id: str
    name: str
    area: str = Field(description="E.g., Health, Work, Personal")
    project: str = Field(description="E.g., Project A, Project B")
    session: str = Field(description="E.g., Evening, After Work, Daytime")
    status: str = Field(description="E.g., Todo, Doing, Done")
    priority: int = Field(default=3, description="1 is highest, 3 is lowest")
    due: datetime = Field(description="Due date")
    effort: int = Field(description="Effort required")
    impact: int = Field(description="Impact of the task")

class Habit(BaseModel):
    id: str
    name: str
    area: str = Field(description="E.g., Health, Work, Personal")
    target_week: int = Field(description="Target number of times to complete the habit per week")

class HabitLog(BaseModel):
    id: str
    date: datetime = Field(description="Date of the log")
    habit: str = Field(description="ID of the habit")
    done: bool = Field(description="Whether the habit was done")