def test_health(client):
    assert client.get('/health').json() == {'status':'ok'}

def test_create_customer(client):
    r = client.post('/customers', json={'name':'Asha','email':'asha@example.com'})
    assert r.status_code == 201
    assert r.json()['id'] > 0

def test_duplicate_customer(client):
    data = {'name':'Asha','email':'asha@example.com'}
    assert client.post('/customers', json=data).status_code == 201
    assert client.post('/customers', json=data).status_code == 409

def test_invoice_customer_required(client):
    assert client.post('/invoices', json={'customer_id':999,'amount_cents':1000}).status_code == 404

def test_invoice_list(client, invoice):
    assert client.get('/invoices').json()[0]['id'] == invoice['id']

def test_partial_then_full(client, invoice):
    iid = invoice['id']
    a = client.post('/payments', json={'invoice_id':iid,'amount_cents':400,'external_reference':'p1'})
    assert a.status_code == 201
    balance = client.get(f'/invoices/{iid}/balance').json()
    assert (balance['outstanding_cents'], balance['status']) == (600,'PARTIALLY_PAID')
    b = client.post('/payments', json={'invoice_id':iid,'amount_cents':600,'external_reference':'p2'})
    assert b.status_code == 201
    assert client.get(f'/invoices/{iid}/balance').json()['status'] == 'PAID'

def test_duplicate_payment(client, invoice):
    data = {'invoice_id':invoice['id'],'amount_cents':100,'external_reference':'dup'}
    assert client.post('/payments', json=data).status_code == 201
    assert client.post('/payments', json=data).status_code == 409
    assert client.get(f"/invoices/{invoice['id']}/balance").json()['paid_cents'] == 100

def test_overpayment_does_not_write(client, invoice):
    iid = invoice['id']
    assert client.post('/payments', json={'invoice_id':iid,'amount_cents':1001,'external_reference':'too-much'}).status_code == 422
    assert client.get(f'/invoices/{iid}/balance').json()['paid_cents'] == 0

def test_unknown_invoice_payment(client):
    assert client.post('/payments', json={'invoice_id':999,'amount_cents':100,'external_reference':'x'}).status_code == 404

def test_unmatched_import(client):
    r = client.post('/payments/import', json={'invoice_id':999,'amount_cents':500,'external_reference':'bank-1'})
    assert r.status_code == 201
    assert r.json()['invoice_id'] is None
    assert client.get('/reconciliation').json()['unmatched_payments'][0]['external_reference'] == 'bank-1'

def test_invalid_amount(client, invoice):
    assert client.post('/payments', json={'invoice_id':invoice['id'],'amount_cents':-1,'external_reference':'neg'}).status_code == 422
