import pytest
from fastapi.testclient import TestClient

from app import FEATURE_COLS, MIN_RELIABLE_MONTHS, app


client = TestClient(app)


def test_health_reports_model_and_explainability():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model"].startswith("CatBoost")
    assert payload["explainability"] == "CatBoost TreeSHAP (exact)"


def test_factories_are_eligible_sorted_and_include_supported_month():
    response = client.get("/factories")

    assert response.status_code == 200
    factories = response.json()
    assert len(factories) == 104
    assert [item["Factory"] for item in factories] == sorted(
        item["Factory"] for item in factories
    )
    templevally = next(item for item in factories if item["Factory"] == "BF0143")
    assert templevally["FactoryName"] == "Templevally"
    assert templevally["latest_prediction_month"] == "2026-01-01"
    assert templevally["latest_reasonable_price"] == pytest.approx(192.438082)


def test_valid_prediction_contract_and_exact_shap_additivity():
    response = client.post(
        "/predict",
        json={"factory": "BF0143", "year": 2026, "month": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    predicted = payload["predicted_reasonable_price"]
    assert predicted == pytest.approx(203.99593725615324)
    assert payload["approx_lower_90"] <= predicted <= payload["approx_upper_90"]
    assert payload["reliability"] in {"HIGH", "MEDIUM", "LOW"}
    assert payload["feature_completeness_pct"] >= 60
    assert payload["reliable_history_months"] >= MIN_RELIABLE_MONTHS
    assert 1 <= len(payload["price_history"]) <= 18
    assert payload["price_history"] == sorted(
        payload["price_history"], key=lambda item: item["month"]
    )

    explanation = payload["explanation"]
    assert explanation["available"] is True
    assert explanation["method"] == "CatBoost TreeSHAP (exact)"
    assert len(explanation["feature_contributions"]) == len(FEATURE_COLS)
    reconstructed_change = explanation["baseline_change_pct"] + sum(
        item["impact_pct_points"]
        for item in explanation["feature_contributions"]
    )
    assert reconstructed_change == pytest.approx(
        explanation["predicted_change_pct"], abs=0.08
    )


def test_prediction_without_a_previous_feature_row_is_blocked():
    response = client.post(
        "/predict",
        json={"factory": "BF0143", "year": 2026, "month": 2},
    )

    assert response.status_code == 400
    assert "No previous-month feature row" in response.json()["detail"]


def test_request_validation_rejects_an_invalid_month():
    response = client.post(
        "/predict",
        json={"factory": "BF0143", "year": 2026, "month": 13},
    )

    assert response.status_code == 422


def test_development_cors_preflight():
    response = client.options(
        "/predict",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_estimate_earnings_uses_predicted_price_times_quantity():
    response = client.post(
        "/estimate-earnings",
        json={"factory": "BF0143", "year": 2026, "month": 1, "expected_leaf_kg": 1250},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["earnings_type"] == "gross"
    assert payload["estimated_gross_earnings_lkr"] == pytest.approx(
        payload["predicted_reasonable_price"] * 1250
    )
    assert payload["gross_earnings_lower_90_lkr"] == pytest.approx(
        payload["approx_lower_90"] * 1250
    )
    assert payload["gross_earnings_upper_90_lkr"] == pytest.approx(
        payload["approx_upper_90"] * 1250
    )


def test_compare_factories_returns_price_ranked_decision_support_results():
    response = client.post(
        "/compare-factories",
        json={"year": 2026, "month": 1, "expected_leaf_kg": 1250, "top_n": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["returned_count"] == 5
    assert payload["eligible_result_count"] >= 5
    prices = [item["predicted_reasonable_price"] for item in payload["results"]]
    assert prices == sorted(prices, reverse=True)
    assert [item["price_rank"] for item in payload["results"]] == [1, 2, 3, 4, 5]
    for item in payload["results"]:
        assert item["estimated_gross_earnings_lkr"] == pytest.approx(
            item["predicted_reasonable_price"] * 1250
        )


def test_earnings_quantity_must_be_positive():
    response = client.post(
        "/estimate-earnings",
        json={"factory": "BF0143", "year": 2026, "month": 1, "expected_leaf_kg": 0},
    )
    assert response.status_code == 422


def test_regions_reports_pending_until_verified_mapping_exists():
    response = client.get('/regions')
    assert response.status_code == 200
    payload = response.json()
    assert payload['eligible_factory_count'] == 104
    assert payload['verified_factory_count'] == 0
    assert payload['status'] == 'pending_mapping'


def test_factory_profile_exposes_geography_contract_without_guessing():
    response = client.get('/factory/BF0143/profile')
    assert response.status_code == 200
    payload = response.json()
    assert payload['factory'] == 'BF0143'
    assert payload['factory_name'] == 'Templevally'
    assert payload['geography_verified'] is False
    assert payload['tea_growing_region'] is None


def test_compare_regional_filter_is_blocked_without_verified_mapping():
    response = client.post(
        '/compare-factories',
        json={
            'year': 2026,
            'month': 1,
            'expected_leaf_kg': 1250,
            'top_n': 5,
            'tea_growing_region': 'Example Region',
        },
    )
    assert response.status_code == 400
    assert 'No verified factory geography mapping' in response.json()['detail']


def test_evaluation_collection_is_disabled_by_default():
    response = client.get('/evaluation/status')
    assert response.status_code == 200
    assert response.json()['collection_enabled'] is False


def test_evaluation_submission_can_be_enabled_for_anonymized_research(monkeypatch, tmp_path):
    import app as app_module

    target = tmp_path / 'responses.csv'
    monkeypatch.setattr(app_module, 'EVALUATION_ENABLED', True)
    monkeypatch.setattr(app_module, 'EVALUATION_DATA_PATH', target)

    body = {
        'role': 'tea smallholder',
        'consent': True,
        'task1_success': True,
        'task2_success': True,
        'task3_success': True,
        'task4_success': True,
        'task5_success': True,
        **{f'sus_q{i}': 4 if i % 2 else 2 for i in range(1, 11)},
        'price_clarity_1to5': 5,
        'earnings_clarity_1to5': 5,
        'uncertainty_clarity_1to5': 4,
        'usefulness_1to5': 5,
        'trust_appropriateness_1to5': 4,
        'comments': 'Clear system.',
    }
    response = client.post('/evaluation/submit', json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'recorded'
    assert payload['sus_score'] == pytest.approx(75.0)
    assert target.is_file()
