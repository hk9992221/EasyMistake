from api.schemas.common import BaseSchema


class AnalyticsOverviewResponse(BaseSchema):
    total_questions: int
    mistake_questions: int
    mastered_questions: int
    due_today: int
    overdue: int
    avg_accuracy_7d: float
    avg_accuracy_30d: float


class ErrorTagItem(BaseSchema):
    error_tag: str
    count: int


class ErrorTagsStatsResponse(BaseSchema):
    items: list[ErrorTagItem]


class MasteryDistributionItem(BaseSchema):
    mastery_level: int
    count: int


class MasteryDistributionResponse(BaseSchema):
    items: list[MasteryDistributionItem]


class KnowledgePointItem(BaseSchema):
    knowledge_point: str
    total_attempts: int
    wrong_attempts: int


class KnowledgePointStatsResponse(BaseSchema):
    items: list[KnowledgePointItem]


class ReviewRetentionResponse(BaseSchema):
    reviewed_count: int
    retained_count: int
    retention_rate: float
