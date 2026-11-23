from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import Customer, Invoice, Payment
from .schemas import CustomerIn, CustomerOut, InvoiceIn, InvoiceOut, PaymentIn, PaymentOut, ImportPaymentIn

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # beginner setup; use Alembic for production migrations
    yield

app = FastAPI(title='InvoiceFlow', description='Educational invoice and payment reconciliation API', lifespan=lifespan)

def paid_amount(db: Session, invoice_id: int) -> int:
    return db.scalar(select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(Payment.invoice_id == invoice_id)) or 0

def duplicate_guard(db: Session, reference: str):
    if db.scalar(select(Payment.id).where(Payment.external_reference == reference)) is not None:
        raise HTTPException(409, 'External payment reference already exists')

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/customers', response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerIn, db: Session = Depends(get_db)):
    customer = Customer(**payload.model_dump())
    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Customer email already exists')
    return customer

@app.post('/invoices', response_model=InvoiceOut, status_code=201)
def create_invoice(payload: InvoiceIn, db: Session = Depends(get_db)):
    if db.get(Customer, payload.customer_id) is None:
        raise HTTPException(404, 'Customer not found')
    invoice = Invoice(**payload.model_dump(), status='UNPAID')
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice

@app.get('/invoices', response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    return db.scalars(select(Invoice).order_by(Invoice.id)).all()

@app.get('/invoices/{invoice_id}', response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, 'Invoice not found')
    return invoice

@app.get('/invoices/{invoice_id}/balance')
def invoice_balance(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, 'Invoice not found')
    paid = paid_amount(db, invoice_id)
    return {'invoice_id': invoice_id, 'amount_cents': invoice.amount_cents, 'paid_cents': paid, 'outstanding_cents': invoice.amount_cents - paid, 'status': invoice.status}

@app.post('/payments', response_model=PaymentOut, status_code=201)
def record_payment(payload: PaymentIn, db: Session = Depends(get_db)):
    duplicate_guard(db, payload.external_reference)
    invoice = db.get(Invoice, payload.invoice_id)
    if invoice is None:
        raise HTTPException(404, 'Invoice not found')
    paid = paid_amount(db, invoice.id)
    if payload.amount_cents > invoice.amount_cents - paid:
        raise HTTPException(422, 'Payment exceeds outstanding balance')
    payment = Payment(**payload.model_dump())
    try:
        db.add(payment)
        db.flush()  # insert payment, but do not commit yet
        new_paid = paid + payment.amount_cents
        invoice.status = 'PAID' if new_paid == invoice.amount_cents else 'PARTIALLY_PAID'
        db.commit()  # both changes succeed or both roll back
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Duplicate payment reference or invalid database reference')
    except Exception:
        db.rollback()
        raise
    return payment

@app.post('/payments/import', response_model=PaymentOut, status_code=201)
def import_payment(payload: ImportPaymentIn, db: Session = Depends(get_db)):
    """Record a bank/import feed item; unknown invoices are kept unmatched.

    Known invoices are processed using the same validations as normal payments.
    """
    duplicate_guard(db, payload.external_reference)
    if payload.invoice_id is not None and db.get(Invoice, payload.invoice_id) is not None:
        return record_payment(PaymentIn(**payload.model_dump()), db)
    payment = Payment(invoice_id=None, amount_cents=payload.amount_cents, external_reference=payload.external_reference)
    try:
        db.add(payment)
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Duplicate external payment reference')
    return payment

@app.get('/reconciliation')
def reconciliation(db: Session = Depends(get_db)):
    invoices = db.scalars(select(Invoice).order_by(Invoice.id)).all()
    unmatched = db.scalars(select(Payment).where(Payment.invoice_id.is_(None)).order_by(Payment.id)).all()
    return {
        'invoices': [{'invoice_id': i.id, 'status': i.status, 'outstanding_cents': i.amount_cents - paid_amount(db, i.id)} for i in invoices],
        'unmatched_payments': [{'payment_id': p.id, 'external_reference': p.external_reference, 'amount_cents': p.amount_cents} for p in unmatched]
    }
