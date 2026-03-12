ALLURE_RESULTS      := allure-results
ALLURE_RESULTS_UI   := allure-results-ui
ALLURE_RESULTS_PACT := allure-results-pact

# The one failing test used for the Jira integration demo
DEMO_TEST := tests/ui/test_smoke.py::test_homepage_has_links_to_core_sections

.PHONY: test test-allure test-ui test-pact report report-ui report-pact demo-fail

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

# ── Jira integration demo ────────────────────────────────────────────────────
# Runs the intentionally-failing navigation-regression test, creates a Jira
# Bug (project KAN) with screenshot + action plan, then opens the Allure report.
#
# Usage:
#   make demo-fail
#
# What it does:
#   1. Runs test_homepage_has_links_to_core_sections (expects /careers link)
#   2. Playwright captures a full-page screenshot on failure
#   3. JiraContextCollector queries KAN for duplicates / similar bugs
#   4. A new Bug is filed in Jira (or existing one updated) with:
#      - Full traceback
#      - Screenshot attachment
#      - Auto-generated action plan
#      - Related issue links
#   5. Context JSON is attached to the Allure report
#   6. Allure report opens automatically in the browser
demo-fail:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo " Jira Integration Demo — running failing UI test"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	JIRA_REPORT_FAILURES=1 pytest "$(DEMO_TEST)" \
	  -v -m ui \
	  --tb=short \
	  --alluredir=$(ALLURE_RESULTS_UI)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo " Opening Allure report…"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	allure serve $(ALLURE_RESULTS_UI)

# Open last Allure report without re-running tests
report:
	allure serve $(ALLURE_RESULTS)

report-ui:
	allure serve $(ALLURE_RESULTS_UI)

report-pact:
	allure serve $(ALLURE_RESULTS_PACT)
