from typing import Dict, Any, List
from pydantic import BaseModel


class OverviewStats(BaseModel):
    """Overview statistics"""
    total_questions: int
    total_attempts: int
    correct_rate: float
    active_paper_sets: int


class AttemptTrend(BaseModel):
    """Attempt trend data point"""
    date: str
    total: int
    correct: int
    wrong: int
    skipped: int


class WrongReasonStat(BaseModel):
    """Wrong reason statistics"""
    reason: str
    count: int
    percentage: float
