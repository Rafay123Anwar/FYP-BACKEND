import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.profile import (
        CandidateSkill,
        Education,
        Experience,
        Profile,
        Project,
        Resume,
    )


class UserRole(str, enum.Enum):
    JOB_SEEKER = "JOB_SEEKER"
    HR = "HR"
    COMPANY_ADMIN = "COMPANY_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        default=UserRole.JOB_SEEKER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships with on-demand loading (prevents cascading SELECTs on user auth)
    profile: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )
    educations: Mapped[list["Education"]] = relationship(
        "Education",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    experiences: Mapped[list["Experience"]] = relationship(
        "Experience",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
