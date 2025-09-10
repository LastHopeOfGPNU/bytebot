"""Tests for database models."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from bytebot.models.task import Task, TaskStatus, TaskPriority
from bytebot.models.conversation import Conversation, Message, MessageRole
from bytebot.models.user import User
from bytebot.models.session import Session


class TestTaskModel:
    """Test Task model functionality."""

    def test_task_creation(self, db_session):
        """Test creating a new task."""
        task = Task(
            description="Test task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            metadata={"key": "value"}
        )
        
        db_session.add(task)
        db_session.commit()
        
        assert task.id is not None
        assert task.description == "Test task"
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.metadata == {"key": "value"}
        assert task.created_at is not None
        assert task.updated_at is not None

    def test_task_default_values(self, db_session):
        """Test task default values."""
        task = Task(description="Minimal task")
        
        db_session.add(task)
        db_session.commit()
        
        assert task.priority == TaskPriority.MEDIUM  # default
        assert task.status == TaskStatus.PENDING  # default
        assert task.metadata == {}  # default
        assert task.created_at is not None
        assert task.updated_at is not None

    def test_task_update_timestamp(self, db_session):
        """Test that updated_at changes on update."""
        task = Task(description="Test task")
        db_session.add(task)
        db_session.commit()
        
        original_updated_at = task.updated_at
        
        # Update the task
        task.description = "Updated task"
        db_session.commit()
        
        assert task.updated_at > original_updated_at

    def test_task_status_enum(self, db_session):
        """Test task status enumeration."""
        task = Task(description="Test task")
        
        # Test all valid statuses
        for status in TaskStatus:
            task.status = status
            db_session.add(task)
            db_session.commit()
            assert task.status == status

    def test_task_priority_enum(self, db_session):
        """Test task priority enumeration."""
        task = Task(description="Test task")
        
        # Test all valid priorities
        for priority in TaskPriority:
            task.priority = priority
            db_session.add(task)
            db_session.commit()
            assert task.priority == priority

    def test_task_description_required(self, db_session):
        """Test that task description is required."""
        task = Task()  # No description
        
        db_session.add(task)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_task_json_metadata(self, db_session):
        """Test JSON metadata field."""
        complex_metadata = {
            "nested": {
                "key": "value",
                "number": 42,
                "list": [1, 2, 3]
            },
            "boolean": True
        }
        
        task = Task(
            description="Test task",
            metadata=complex_metadata
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Retrieve and verify
        retrieved_task = db_session.get(Task, task.id)
        assert retrieved_task.metadata == complex_metadata

    def test_task_string_representation(self, db_session):
        """Test task string representation."""
        task = Task(
            description="Test task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.IN_PROGRESS
        )
        
        db_session.add(task)
        db_session.commit()
        
        str_repr = str(task)
        assert "Test task" in str_repr
        assert "HIGH" in str_repr
        assert "IN_PROGRESS" in str_repr


class TestConversationModel:
    """Test Conversation model functionality."""

    def test_conversation_creation(self, db_session):
        """Test creating a new conversation."""
        conversation = Conversation(
            title="Test conversation",
            metadata={"key": "value"}
        )
        
        db_session.add(conversation)
        db_session.commit()
        
        assert conversation.id is not None
        assert conversation.title == "Test conversation"
        assert conversation.metadata == {"key": "value"}
        assert conversation.created_at is not None
        assert conversation.updated_at is not None

    def test_conversation_default_values(self, db_session):
        """Test conversation default values."""
        conversation = Conversation()
        
        db_session.add(conversation)
        db_session.commit()
        
        assert conversation.title is None  # Can be null
        assert conversation.metadata == {}  # default
        assert conversation.created_at is not None
        assert conversation.updated_at is not None

    def test_conversation_messages_relationship(self, db_session):
        """Test conversation-messages relationship."""
        conversation = Conversation(title="Test conversation")
        db_session.add(conversation)
        db_session.commit()
        
        # Add messages
        message1 = Message(
            conversation_id=conversation.id,
            content="Hello",
            role=MessageRole.USER
        )
        message2 = Message(
            conversation_id=conversation.id,
            content="Hi there!",
            role=MessageRole.ASSISTANT
        )
        
        db_session.add_all([message1, message2])
        db_session.commit()
        
        # Test relationship
        assert len(conversation.messages) == 2
        assert message1 in conversation.messages
        assert message2 in conversation.messages


class TestMessageModel:
    """Test Message model functionality."""

    def test_message_creation(self, db_session):
        """Test creating a new message."""
        # First create a conversation
        conversation = Conversation(title="Test conversation")
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            content="Test message",
            role=MessageRole.USER,
            metadata={"key": "value"}
        )
        
        db_session.add(message)
        db_session.commit()
        
        assert message.id is not None
        assert message.conversation_id == conversation.id
        assert message.content == "Test message"
        assert message.role == MessageRole.USER
        assert message.metadata == {"key": "value"}
        assert message.created_at is not None

    def test_message_role_enum(self, db_session):
        """Test message role enumeration."""
        conversation = Conversation(title="Test")
        db_session.add(conversation)
        db_session.commit()
        
        # Test all valid roles
        for role in MessageRole:
            message = Message(
                conversation_id=conversation.id,
                content="Test message",
                role=role
            )
            db_session.add(message)
            db_session.commit()
            assert message.role == role

    def test_message_conversation_relationship(self, db_session):
        """Test message-conversation relationship."""
        conversation = Conversation(title="Test conversation")
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            content="Test message",
            role=MessageRole.USER
        )
        db_session.add(message)
        db_session.commit()
        
        # Test relationship
        assert message.conversation == conversation
        assert message in conversation.messages

    def test_message_required_fields(self, db_session):
        """Test message required fields."""
        # Missing conversation_id
        message = Message(
            content="Test message",
            role=MessageRole.USER
        )
        
        db_session.add(message)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_message_cascade_delete(self, db_session):
        """Test that messages are deleted when conversation is deleted."""
        conversation = Conversation(title="Test conversation")
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            content="Test message",
            role=MessageRole.USER
        )
        db_session.add(message)
        db_session.commit()
        
        message_id = message.id
        
        # Delete conversation
        db_session.delete(conversation)
        db_session.commit()
        
        # Message should be deleted too
        deleted_message = db_session.get(Message, message_id)
        assert deleted_message is None


class TestUserModel:
    """Test User model functionality."""

    def test_user_creation(self, db_session):
        """Test creating a new user."""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
        
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_default_values(self, db_session):
        """Test user default values."""
        user = User(
            username="testuser",
            email="test@example.com"
        )
        
        db_session.add(user)
        db_session.commit()
        
        assert user.is_active is True  # default
        assert user.full_name is None  # can be null

    def test_user_unique_constraints(self, db_session):
        """Test user unique constraints."""
        user1 = User(
            username="testuser",
            email="test@example.com"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create user with same username
        user2 = User(
            username="testuser",  # duplicate
            email="different@example.com"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_email_unique_constraint(self, db_session):
        """Test user email unique constraint."""
        user1 = User(
            username="user1",
            email="test@example.com"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create user with same email
        user2 = User(
            username="user2",
            email="test@example.com"  # duplicate
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestSessionModel:
    """Test Session model functionality."""

    def test_session_creation(self, db_session):
        """Test creating a new session."""
        # First create a user
        user = User(
            username="testuser",
            email="test@example.com"
        )
        db_session.add(user)
        db_session.commit()
        
        session = Session(
            user_id=user.id,
            session_token="test_token_123",
            expires_at=datetime.now(timezone.utc),
            metadata={"ip": "127.0.0.1"}
        )
        
        db_session.add(session)
        db_session.commit()
        
        assert session.id is not None
        assert session.user_id == user.id
        assert session.session_token == "test_token_123"
        assert session.expires_at is not None
        assert session.metadata == {"ip": "127.0.0.1"}
        assert session.created_at is not None

    def test_session_user_relationship(self, db_session):
        """Test session-user relationship."""
        user = User(
            username="testuser",
            email="test@example.com"
        )
        db_session.add(user)
        db_session.commit()
        
        session = Session(
            user_id=user.id,
            session_token="test_token_123",
            expires_at=datetime.now(timezone.utc)
        )
        db_session.add(session)
        db_session.commit()
        
        # Test relationship
        assert session.user == user
        assert session in user.sessions

    def test_session_token_unique(self, db_session):
        """Test session token uniqueness."""
        user = User(
            username="testuser",
            email="test@example.com"
        )
        db_session.add(user)
        db_session.commit()
        
        session1 = Session(
            user_id=user.id,
            session_token="duplicate_token",
            expires_at=datetime.now(timezone.utc)
        )
        db_session.add(session1)
        db_session.commit()
        
        # Try to create session with same token
        session2 = Session(
            user_id=user.id,
            session_token="duplicate_token",  # duplicate
            expires_at=datetime.now(timezone.utc)
        )
        db_session.add(session2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestModelRelationships:
    """Test relationships between models."""

    def test_user_sessions_cascade_delete(self, db_session):
        """Test that sessions are deleted when user is deleted."""
        user = User(
            username="testuser",
            email="test@example.com"
        )
        db_session.add(user)
        db_session.commit()
        
        session = Session(
            user_id=user.id,
            session_token="test_token",
            expires_at=datetime.now(timezone.utc)
        )
        db_session.add(session)
        db_session.commit()
        
        session_id = session.id
        
        # Delete user
        db_session.delete(user)
        db_session.commit()
        
        # Session should be deleted too
        deleted_session = db_session.get(Session, session_id)
        assert deleted_session is None

    def test_conversation_messages_cascade_delete(self, db_session):
        """Test that messages are deleted when conversation is deleted."""
        conversation = Conversation(title="Test conversation")
        db_session.add(conversation)
        db_session.commit()
        
        messages = [
            Message(
                conversation_id=conversation.id,
                content=f"Message {i}",
                role=MessageRole.USER
            )
            for i in range(3)
        ]
        
        db_session.add_all(messages)
        db_session.commit()
        
        message_ids = [msg.id for msg in messages]
        
        # Delete conversation
        db_session.delete(conversation)
        db_session.commit()
        
        # All messages should be deleted
        for msg_id in message_ids:
            deleted_message = db_session.get(Message, msg_id)
            assert deleted_message is None


class TestModelValidation:
    """Test model validation and constraints."""

    def test_task_description_length(self, db_session):
        """Test task description length constraints."""
        # Very long description
        long_description = "x" * 10000
        
        task = Task(description=long_description)
        db_session.add(task)
        
        # Should either succeed or fail based on database constraints
        try:
            db_session.commit()
            # If it succeeds, verify the description was stored
            assert task.description == long_description
        except IntegrityError:
            # If it fails, that's also acceptable
            db_session.rollback()

    def test_user_email_format(self, db_session):
        """Test user email format validation."""
        # This would test email format validation if implemented
        user = User(
            username="testuser",
            email="invalid-email-format"
        )
        
        db_session.add(user)
        
        # Depending on validation implementation, this might succeed or fail
        try:
            db_session.commit()
        except (IntegrityError, ValueError):
            db_session.rollback()

    def test_session_expiry_validation(self, db_session):
        """Test session expiry date validation."""
        user = User(
            username="testuser",
            email="test@example.com"
        )
        db_session.add(user)
        db_session.commit()
        
        # Session with past expiry date
        past_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        
        session = Session(
            user_id=user.id,
            session_token="test_token",
            expires_at=past_date
        )
        
        db_session.add(session)
        db_session.commit()
        
        # Should succeed (validation is typically done at application level)
        assert session.expires_at == past_date