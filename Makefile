ALLURE_RESULTS     := allure-results
ALLURE_RESULTS_UI  := allure-results-ui
ALLURE_RESULTS_PACT := allure-results-pact

.PHONY: test test-allure test-ui test-pact report report-ui report-pact

# Run all backend tests (no report)
test:
	pytest \
	  --ignore=tests/postman \
	  --ignore=tests/ui \
	  --ignore=tests/api/test_openapi.py \
	  --ignore=tests/performance/test_benchmarks.py \
	  --cov=src --cov-branch --cov-fail-under=80 \
	  -q

# Run all backend tests + open Allure report automatically
test-allure:
	pytest \
	  --ignore=tests/postman \
	  --ignore=tests/ui \
	  --ignore=tests/api/test_openapi.py \
	  --ignore=tests/performance/test_benchmarks.py \
	  --cov=src --cov-branch --cov-fail-under=80 \
	  --alluredir=$(ALLURE_RESULTS) \
	  -q
	allure serve $(ALLURE_RESULTS)

# Run UI tests + open Allure report automatically
test-ui:
	pytest tests/ui -m ui --tb=short --alluredir=$(ALLURE_RESULTS_UI)
	allure serve $(ALLURE_RESULTS_UI)

# Run Pact consumer + provider verification tests sequentially
# Consumer tests generate pact files; provider verification reads them
test-pact:
	pytest tests/pact/test_users_consumer.py -m contract --alluredir=$(ALLURE_RESULTS_PACT) -v
	pytest tests/pact/test_users_provider.py tests/pact/test_breaking_change.py -m contract --alluredir=$(ALLURE_RESULTS_PACT) -v
	allure serve $(ALLURE_RESULTS_PACT)

# Open last Allure report without re-running tests
report:
	allure serve $(ALLURE_RESULTS)

report-ui:
	allure serve $(ALLURE_RESULTS_UI)

report-pact:
	allure serve $(ALLURE_RESULTS_PACT)
