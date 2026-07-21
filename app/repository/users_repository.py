from sqlalchemy import select

from app.database.connection import get_session
from app.models.user import AppUser, UserDocument, document_to_dict, user_to_dict


def find_user_by_username(username):
    with get_session() as session:
        user = session.execute(select(AppUser).where(AppUser.username == username)).scalar_one_or_none()
        return user_to_dict(user)


def create_user(username, password_hash):
    with get_session() as session:
        session.add(AppUser(username=username, password_hash=password_hash))
        session.commit()


def deactivate_active_documents(user_id):
    with get_session() as session:
        docs = session.execute(
            select(UserDocument).where(UserDocument.user_id == user_id, UserDocument.is_active.is_(True))
        ).scalars().all()
        for doc in docs:
            doc.is_active = False
        session.commit()


def create_document(user_id, filename, file_format, file_bytes, data_json, row_count, is_active=True):
    with get_session() as session:
        document = UserDocument(
            user_id=user_id,
            filename=filename,
            file_format=file_format,
            file_bytes=file_bytes,
            data_json=data_json,
            row_count=row_count,
            is_active=is_active,
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        return document_to_dict(document)


def get_document_by_id(user_id, document_id):
    with get_session() as session:
        document = session.execute(
            select(UserDocument).where(UserDocument.id == document_id, UserDocument.user_id == user_id)
        ).scalar_one_or_none()
        return document_to_dict(document)


def get_latest_active_document(user_id):
    with get_session() as session:
        document = session.execute(
            select(UserDocument)
            .where(UserDocument.user_id == user_id, UserDocument.is_active.is_(True))
            .order_by(UserDocument.uploaded_at.desc(), UserDocument.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        return document_to_dict(document)


def list_documents(user_id):
    with get_session() as session:
        documents = session.execute(
            select(UserDocument)
            .where(UserDocument.user_id == user_id)
            .order_by(UserDocument.uploaded_at.desc(), UserDocument.id.desc())
        ).scalars().all()
        return [document_to_dict(document, include_data=False) for document in documents]


def update_document_fields(user_id, document_id, **fields):
    with get_session() as session:
        document = session.execute(
            select(UserDocument).where(UserDocument.id == document_id, UserDocument.user_id == user_id)
        ).scalar_one_or_none()
        if document is None:
            return None

        for key, value in fields.items():
            setattr(document, key, value)
        session.commit()
        session.refresh(document)
        return document_to_dict(document)
