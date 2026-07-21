from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, LargeBinary, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")


class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(Text, nullable=False)
    file_format = Column(Text, nullable=False)
    file_bytes = Column(LargeBinary, nullable=False)
    data_json = Column(JSONB, nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_active = Column(Boolean, nullable=False, default=True)

    user = relationship("AppUser", back_populates="documents")


Index("idx_user_documents_user_id", UserDocument.user_id)


def user_to_dict(user):
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "password_hash": user.password_hash,
        "created_at": user.created_at,
    }


def document_to_dict(document, include_data=True):
    if not document:
        return None
    payload = {
        "id": document.id,
        "user_id": document.user_id,
        "filename": document.filename,
        "file_format": document.file_format,
        "row_count": document.row_count,
        "uploaded_at": document.uploaded_at,
        "is_active": document.is_active,
    }
    if include_data:
        payload["file_bytes"] = document.file_bytes
        payload["data_json"] = document.data_json
    return payload
