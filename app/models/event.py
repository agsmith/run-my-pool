from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class CardView(BaseModel):
    title: str
    fields: List[Dict[str, Any]] = []
    colour: Optional[str]
    bg_color: Optional[str]


class TimelineView(BaseModel):
    day: datetime
    month: Optional[str] = None
    month_name: Optional[str] = None
    time_only: Optional[str] = None
    day_name: Optional[str] = None
    day_with_suffix: Optional[str] = None
    status: Optional[str] = None
    channel: Optional[str] = None
    operation: Optional[str] = None
    instrument: Optional[str] = None
    token_tail: Optional[str] = None
    amount: Optional[float] = None
    error: Optional[str] = None
    error_desc: Optional[str] = None


class Timeline(BaseModel):
    baid: Optional[str]
    custid: Optional[str]
    txn_time: Optional[datetime]
    channel: Optional[str]
    instrument: Optional[Any]
    amount: Optional[float]
    operation: Optional[str]
    token_tail: Optional[str]
    exception: Optional[str]
    excptn_desc: Optional[str]


class ProfileData(BaseModel):
    timeline: List[Timeline] = []
    cards: Optional[List[Dict[str, Any]]] = None
    profileRank: Optional[str] = None
    activated: List[str] = None


class EventPageModel(BaseModel):
    cardview: List[CardView] = []
    timelineview: List[TimelineView] = []
