from pydantic import BaseModel, ConfigDict, Field

class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=255)

class CustomerOut(CustomerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int

class InvoiceIn(BaseModel):
    customer_id: int
    amount_cents: int = Field(gt=0)

class InvoiceOut(InvoiceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str

class PaymentIn(BaseModel):
    invoice_id: int
    amount_cents: int = Field(gt=0)
    external_reference: str = Field(min_length=1, max_length=100)

class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int | None
    amount_cents: int
    external_reference: str

class ImportPaymentIn(BaseModel):
    invoice_id: int | None = None
    amount_cents: int = Field(gt=0)
    external_reference: str = Field(min_length=1, max_length=100)
