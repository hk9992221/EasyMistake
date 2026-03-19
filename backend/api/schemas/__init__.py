# Import all schemas
from api.schemas.common import *
from api.schemas.user import *
from api.schemas.image import *
from api.schemas.paper import *
from api.schemas.question import *
from api.schemas.answer import *
from api.schemas.extraction import *
from api.schemas.attempt import *
from api.schemas.submission import *
from api.schemas.paper_set import *
from api.schemas.export import *
from api.schemas.job import *
from api.schemas.stats import *
from api.schemas.question_progress import *
from api.schemas.review import *
from api.schemas.analytics import *

__all__ = [
    # Common
    "BaseSchema",
    "TimestampsSchema",
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",

    # User
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserResponse",
    "Token",
    "InviteCreate",
    "InviteResponse",

    # Image
    "ImageBase",
    "ImageCreate",
    "ImageUpdate",
    "ImageResponse",
    "UploadUrlResponse",
    "ImageUploadUrlRequest",

    # Paper
    "PaperBase",
    "PaperCreate",
    "PaperUpdate",
    "PaperResponse",

    # Question
    "QuestionBase",
    "QuestionCreate",
    "QuestionUpdate",
    "QuestionResponse",
    "QuestionListParams",

    # Answer
    "AnswerBase",
    "AnswerCreate",
    "AnswerUpdate",
    "AnswerResponse",

    # Extraction
    "ExtractionBase",
    "ExtractionCreate",
    "ExtractionUpdate",
    "ExtractionResponse",
    "DraftQuestion",
    "DraftQuestionsResponse",

    # Attempt
    "AttemptBase",
    "AttemptCreate",
    "AttemptUpdate",
    "AttemptResponse",

    # Submission
    "SubmissionBase",
    "SubmissionCreate",
    "SubmissionUpdate",
    "SubmissionResponse",
    "SubmissionItemBase",
    "SubmissionItemUpdate",
    "SubmissionItemResponse",
    "BatchUpsertItem",
    "BatchUpsertRequest",

    # Paper Set
    "PaperSetBase",
    "PaperSetCreate",
    "PaperSetUpdate",
    "PaperSetResponse",
    "PaperSetItemCreate",
    "PaperSetItemUpdate",
    "PaperSetItemResponse",
    "PreviewQuestion",
    "PaperSetPreviewResponse",
    "BatchUpsertPaperSetItem",
    "BatchUpsertPaperSetRequest",

    # Export
    "ExportBase",
    "ExportCreate",
    "ExportResponse",
    "DownloadUrlResponse",

    # Job
    "JobBase",
    "JobCreate",
    "JobResponse",

    # Stats
    "OverviewStats",
    "AttemptTrend",
    "WrongReasonStat",

    # Question Progress
    "QuestionProgressCreate",
    "QuestionProgressUpdate",
    "QuestionProgressResponse",
    "QuestionProgressListResponse",
    "ReviewCompleteRequest",

    # Review
    "ReviewQueueItem",
    "ReviewQueueResponse",

    # Analytics
    "AnalyticsOverviewResponse",
    "ErrorTagItem",
    "ErrorTagsStatsResponse",
    "MasteryDistributionItem",
    "MasteryDistributionResponse",
    "KnowledgePointItem",
    "KnowledgePointStatsResponse",
    "ReviewRetentionResponse",
]
