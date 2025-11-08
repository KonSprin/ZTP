from behave import given, when, then # type: ignore
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
response = None

@given(u'API dziala')
def step_api_running (context):
    assert client is not None

@when(u'wysylam żądanie POST na "/users" z')
def step_send_post(context):
    global response
    for row in context.table:
        print({"name": row['name'], "email": row['email']})
        response = client.post("http://localhost:8000/users", json={"name": row['name'], "email": row['email']})

@then(u'odpowiedź ma status 200')
def step_check_status (context) :
    assert response.status_code == 200

@then(u'odpowiedź zawiera uzytkownika "{name}"')
def step_check_user (context, name):
    data = response.json()
    assert data["name"] == name
