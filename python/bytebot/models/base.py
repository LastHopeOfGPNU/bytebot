"""Base model class with common fields and methods."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    # Generate table name automatically from class name
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        """Convert model instance to dictionary.
        
        Args:
            exclude: Set of field names to exclude from the dictionary
        
        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or set()
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Convert datetime objects to ISO format strings
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude: Optional[set] = None) -> None:
        """Update model instance from dictionary.
        
        Args:
            data: Dictionary with field values
            exclude: Set of field names to exclude from update
        """
        exclude = exclude or set()
        
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        
        # Try to get an ID field for representation
        id_value = None
        for attr in ['id', 'uuid', 'name', 'title']:
            if hasattr(self, attr):
                id_value = getattr(self, attr)
                break
        
        if id_value is not None:
            return f"<{class_name}({id_value})>"
        else:
            return f"<{class_name}>"


class TimestampMixin:
    """Mixin for models that need created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the record was last updated"
    )


class SoftDeleteMixin:
    """Mixin for models that support soft deletion."""
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Timestamp when the record was soft deleted"
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark the record as soft deleted."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.deleted_at = None


class UUIDMixin:
    """Mixin for models that use UUID as primary key."""
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        doc="UUID primary key"
    )
    
    def __init__(self, **kwargs):
        """Initialize with UUID if not provided."""
        if 'id' not in kwargs:
            import uuid
            kwargs['id'] = str(uuid.uuid4())
        super().__init__(**kwargs)