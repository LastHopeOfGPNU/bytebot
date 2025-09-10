"""Summary-related types and enumerations."""

from enum import Enum


class SummaryType(str, Enum):
    """Types of summaries."""
    EXECUTION = "execution"
    ERROR = "error"
    COMPLETION = "completion"
    PROGRESS = "progress"
    ANALYSIS = "analysis"
    DECISION = "decision"
    RECOMMENDATION = "recommendation"
    INSIGHT = "insight"
    FEEDBACK = "feedback"
    REVIEW = "review"


class SummaryStatus(str, Enum):
    """Status of summaries."""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PUBLISHED = "published"
    HIDDEN = "hidden"


class SummaryQualityLevel(str, Enum):
    """Quality levels for summaries."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXCELLENT = "excellent"


class SummaryPriority(str, Enum):
    """Priority levels for summaries."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SummaryVisibility(str, Enum):
    """Visibility levels for summaries."""
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"
    TEAM = "team"
    ORGANIZATION = "organization"