ALLURE_RESULTS     := allure-results
ALLURE_RESULTS_UI  := allure-results-ui

.PHONY: test test-allure test-ui report report-ui

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

# Open last Allure report without re-running tests
report:
	allure serve $(ALLURE_RESULTS)

report-ui:
	allure serve $(ALLURE_RESULTS_UI)
