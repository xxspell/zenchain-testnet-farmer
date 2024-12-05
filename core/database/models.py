import enum

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()




class ActionStatus(enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class ActionType(enum.Enum):
    WAITLIST = "waitlist"
    FAUCET = "faucet"
    BRIDGE = "bridge"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    address = Column(String, unique=True)
    private_key = Column(String)
    proxy = Column(String)
    headers = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    active = Column(Boolean)


    actions = relationship("Action", back_populates="account")

    __table_args__ = (
        UniqueConstraint('email', name='unique_email'),
        UniqueConstraint('private_key', name='unique_private_key'),
        UniqueConstraint('address', name='unique_address')
    )

    def __repr__(self):
        return f"<Account(id={self.id}, email={self.email}, address={self.address})>"


class Action(Base):
    __tablename__ = 'actions'

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    account = relationship("Account", back_populates="actions")
    action_type = Column(Enum(ActionType), nullable=False)
    status = Column(Enum(ActionStatus), default=ActionStatus.PENDING)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Action(id={self.id}, type={self.action_type}, status={self.status})>"




