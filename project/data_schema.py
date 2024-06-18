from typing import List, Tuple
from pydantic import BaseModel, model_validator


class Student(BaseModel):
    """
    The Student and the ossociated data with that student
    """
    id: int
    projects: List[int] # list of project ids the student selected
    negatives: List[int] # list of projects explicitly not chosen
    skill: int # 0 = programmer, 1 = writer
    programing_skills: dict

    class Config:
        frozen = False


class Project(BaseModel):
    id: int
    min: int # minimum number of students
    max: int # maximum number of students

    class Config:
        frozen = True


class Instance(BaseModel):
    """
    SEP Assignment Instance
    """
    students: List[Student]
    projects: List[Project]
    programming_languages: List[str]

    class Config:
        frozen = True


class Solution(BaseModel):
    """
    This class represents the solution to an Instance.
    It holds a list representing the project assignments, for each student.
    """
    assignments: List[Tuple[int, int]] # list of tuples from student id to project id.

    class Config:
        frozen = True

