from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class GlobalButton(BaseModel):
    type: str
    title: str


class Option(BaseModel):
    type: str
    title: str
    description: Optional[str]
    postbackText: str


class Item(BaseModel):
    title: str
    subtitle: Optional[str]
    options: List[Option]


class ListModel(BaseModel):
    type: str
    title: Optional[str]
    body: str
    msgid: Optional[str]
    globalButtons: List[GlobalButton]
    items: List[Item]
