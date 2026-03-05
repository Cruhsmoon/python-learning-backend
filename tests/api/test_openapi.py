import schemathesis
from schemathesis import Case


schema = schemathesis.from_uri("http://localhost:8000/openapi.json")


@schema.parametrize()
def test_api(case: Case):
    response = case.call()
    case.validate_response(response)