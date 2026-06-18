"""SQLAlchemy ORM models — all tables defined here."""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Numeric, Text, ForeignKey, JSON, BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="free")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user")  # super_admin | admin | user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")


class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)  # pdf | docx | txt | url
    source_url = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending | processing | completed | failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="documents")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(500), nullable=True)
    channel = Column(String(50), default="web")  # web | whatsapp | slack
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    faithfulness = Column(Numeric(3, 2), nullable=True)              # 0.00–1.00 self-check
    requires_clarification = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class EphemeralChunk(Base):
    """Chunks for user-uploaded files (WhatsApp / chat). 1-hour TTL.

    NOT mixed with the tenant knowledge base. Cron job purges by expires_at.
    """
    __tablename__ = "ephemeral_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(Text, nullable=False)
    # embedding column is vector(1024) — managed by raw SQL / init.sql; not mapped via ORM.
    chunk_index = Column(Integer, nullable=False)
    source_name = Column(String(500), nullable=True)
    extra_metadata = Column("metadata", JSON, default=dict)
    expires_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.utcnow() + timedelta(hours=1))
    created_at = Column(DateTime, default=datetime.utcnow)


class UploadAudit(Base):
    """Per-tenant upload audit log (for hourly quota enforcement)."""
    __tablename__ = "upload_audit"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    bytes = Column(BigInteger, default=0)


class WhatsAppTenantMap(Base):
    __tablename__ = "whatsapp_tenant_map"
    phone_number = Column(String(20), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
