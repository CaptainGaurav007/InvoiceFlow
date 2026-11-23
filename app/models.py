from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    invoices: Mapped[list['Invoice']] = relationship(back_populates='customer')

class Invoice(Base):
    __tablename__ = 'invoices'
    __table_args__ = (CheckConstraint('amount_cents > 0', name='positive_invoice_amount'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'))
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default='UNPAID')
    customer: Mapped[Customer] = relationship(back_populates='invoices')
    payments: Mapped[list['Payment']] = relationship(back_populates='invoice')

class Payment(Base):
    __tablename__ = 'payments'
    __table_args__ = (CheckConstraint('amount_cents > 0', name='positive_payment_amount'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey('invoices.id'), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    external_reference: Mapped[str] = mapped_column(String(100), unique=True)
    invoice: Mapped[Invoice | None] = relationship(back_populates='payments')
