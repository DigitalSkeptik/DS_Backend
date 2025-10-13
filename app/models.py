# SQL Alchemy models declaration.
# https://docs.sqlalchemy.org/en/20/orm/quickstart.html#declare-models
# mapped_column syntax from SQLAlchemy 2.0.

# https://alembic.sqlalchemy.org/en/latest/tutorial.html
# Note, it is used by alembic migrations logic, see `alembic/env.py`

# Alembic shortcuts:
# # create migration
# alembic revision --autogenerate -m "migration_name"

# # apply all migrations
# alembic upgrade head


import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base):
    __tablename__ = "user"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True, index=True
    )
    pass_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True, index=True
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    completed_courses: Mapped[list["CompletedCourse"]] = relationship(
        back_populates="user"
    )
    completed_modules: Mapped[list["CompletedModule"]] = relationship(
        back_populates="user"
    )
    discounts: Mapped[list["Discount"]] = relationship(back_populates="user")
    purchased_courses: Mapped[list["PurchasedCourse"]] = relationship(
        back_populates="user"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    refresh_token: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True, index=True
    )
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.UniqueID", ondelete="CASCADE"),
    )
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Course(Base):
    __tablename__ = "course"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    img_id: Mapped[str] = mapped_column(String(256), nullable=True)

    # Relationships
    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    completed_courses: Mapped[list["CompletedCourse"]] = relationship(
        back_populates="course"
    )
    discounts: Mapped[list["Discount"]] = relationship(back_populates="course")
    purchased_courses: Mapped[list["PurchasedCourse"]] = relationship(
        back_populates="course"
    )
    tags: Mapped[list["CourseTag"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class Module(Base):
    __tablename__ = "module"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.UniqueID", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    position: Mapped[int] = mapped_column(nullable=False)

    # Relationships
    course: Mapped["Course"] = relationship(back_populates="modules")
    tests: Mapped[list["Test"]] = relationship(
        back_populates="module", cascade="all, delete-orphan"
    )
    completed_modules: Mapped[list["CompletedModule"]] = relationship(
        back_populates="module"
    )


class Test(Base):
    __tablename__ = "test"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    module_id: Mapped[str] = mapped_column(
        ForeignKey("module.UniqueID", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    questions: Mapped[list["Question"]] = relationship(
        back_populates="test", cascade="all, delete-orphan"
    )
    module: Mapped["Module"] = relationship(back_populates="tests")


class Question(Base):
    __tablename__ = "question"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    test_id: Mapped[str] = mapped_column(
        ForeignKey("test.UniqueID", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    test: Mapped["Test"] = relationship(back_populates="questions")
    answer_options: Mapped[list["AnswerOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class AnswerOption(Base):
    __tablename__ = "answer_option"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("question.UniqueID", ondelete="CASCADE"), nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    question: Mapped["Question"] = relationship(back_populates="answer_options")


class CompletedCourse(Base):
    __tablename__ = "completed_courses"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.UniqueID", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.UniqueID", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="completed_courses")
    course: Mapped["Course"] = relationship(back_populates="completed_courses")


class CompletedModule(Base):
    __tablename__ = "completed_modules"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.UniqueID", ondelete="CASCADE"), nullable=False
    )
    module_id: Mapped[str] = mapped_column(
        ForeignKey("module.UniqueID", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="completed_modules")
    module: Mapped["Module"] = relationship(back_populates="completed_modules")


class Discount(Base):
    __tablename__ = "discounts"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.UniqueID", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.UniqueID", ondelete="CASCADE"), nullable=False
    )
    percents: Mapped[int] = mapped_column(nullable=False)  # Discount percentage

    # Relationships
    user: Mapped["User"] = relationship(back_populates="discounts")
    course: Mapped["Course"] = relationship(back_populates="discounts")


class PurchasedCourse(Base):
    __tablename__ = "purchased_courses"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.UniqueID", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.UniqueID", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="purchased_courses")
    course: Mapped["Course"] = relationship(back_populates="purchased_courses")


class Tag(Base):
    __tablename__ = "tag"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    content: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)

    # Relationships
    courses: Mapped[list["CourseTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class CourseTag(Base):
    __tablename__ = "course_tags"

    unique_id: Mapped[str] = mapped_column(
        "UniqueID",
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda _: str(uuid.uuid4()),
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("course.UniqueID", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[str] = mapped_column(
        ForeignKey("tag.UniqueID", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    course: Mapped["Course"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="courses")
