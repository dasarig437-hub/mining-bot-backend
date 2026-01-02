from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Boolean,
    DateTime,
    Index,
)
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=True)

    balance = Column(BigInteger, default=0)
    energy = Column(Integer, default=500)

    ads_watched = Column(Integer, default=0)

    referred_by = Column(BigInteger, nullable=True)

    is_banned = Column(Boolean, default=False)

    last_active = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    __table_args__ = (
        Index("idx_users_referred_by", "referred_by"),
        Index("idx_users_last_active", "last_active"),
    )
