from dataclasses import dataclass

import pytest

from scripts.generate_initial_scores import generate_initial_scores
from scripts.update_confidence_schema import update_schema, verify_schema_update
from scripts.validate_confidence_scores import validate_scores
from services.confidence.models import Error, ErrorCode, Success


class FakeResult:
    def __init__(self, *, single=None, data=None):
        self._single = single
        self._data = data or []

    async def single(self):
        return self._single

    async def data(self):
        return self._data


class FakeSession:
    def __init__(self, results):
        self._results = results
        self._calls = []
        self._index = 0

    async def run(self, query, parameters=None):
        parameters = parameters or {}
        self._calls.append({"query": query.strip(), "parameters": parameters})
        result = self._results[self._index]
        self._index += 1
        return result

    @property
    def calls(self):
        return self._calls


class FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeDriver:
    def __init__(self, session):
        self._session = session

    def session(self):
        return FakeSessionContext(self._session)


@pytest.mark.asyncio
async def test_update_schema_sets_properties():
    session = FakeSession([FakeResult(single={"updated_count": 3})])
    driver = FakeDriver(session)

    result = await update_schema(driver, default_tau=9)

    assert result == {"status": "success", "updated_count": 3}
    assert "SET c.confidence_score" in session.calls[0]["query"]
    assert session.calls[0]["parameters"] == {"default_tau": 9}


@pytest.mark.asyncio
async def test_verify_schema_update_reports_missing():
    session = FakeSession([FakeResult(single={"missing_properties_count": 2})])
    driver = FakeDriver(session)

    result = await verify_schema_update(driver)

    assert result == {"valid": False, "missing_count": 2}


@dataclass
class FakeUnderstandingCalculator:
    outcomes: list

    async def calculate_understanding_score(self, concept_id):
        return self.outcomes.pop(0)


@dataclass
class FakeRetentionCalculator:
    outcomes: list

    async def calculate_retention_score(self, concept_id, tau=None):
        return self.outcomes.pop(0)


class FakeCacheManager:
    def __init__(self):
        self.calls = []

    async def set_cached_score(self, concept_id, score, ttl=None):
        self.calls.append((concept_id, score))


class FakeCompositeCalculator:
    def __init__(self, understanding_outcomes, retention_outcomes):
        self.understanding_weight = 0.6
        self.retention_weight = 0.4
        self.understanding_calc = FakeUnderstandingCalculator(understanding_outcomes)
        self.retention_calc = FakeRetentionCalculator(retention_outcomes)


@pytest.mark.asyncio
async def test_generate_initial_scores_successful_run():
    session = FakeSession(
        [
            FakeResult(
                data=[
                    {"concept_id": "concept-1"},
                    {"concept_id": "concept-2"},
                ]
            ),
            FakeResult(),  # update concept-1
            FakeResult(),  # update concept-2
        ]
    )

    calculator = FakeCompositeCalculator(
        understanding_outcomes=[Success(0.8), Success(0.6)],
        retention_outcomes=[Success(0.5), Success(0.4)],
    )
    cache_manager = FakeCacheManager()

    summary = await generate_initial_scores(
        session,
        calculator,
        cache_manager,
        batch_size=2,
        default_tau=7,
    )

    assert summary["total"] == 2
    assert summary["successful"] == 2
    assert summary["failed"] == 0
    assert len(cache_manager.calls) == 2
    assert session.calls[1]["parameters"]["concept_id"] == "concept-1"


@pytest.mark.asyncio
async def test_generate_initial_scores_handles_failure():
    session = FakeSession(
        [
            FakeResult(data=[{"concept_id": "concept-1"}]),
        ]
    )

    calculator = FakeCompositeCalculator(
        understanding_outcomes=[Error("missing explanation", ErrorCode.VALIDATION_ERROR)],
        retention_outcomes=[Success(0.4)],
    )
    cache_manager = FakeCacheManager()

    summary = await generate_initial_scores(
        session,
        calculator,
        cache_manager,
    )

    assert summary["total"] == 1
    assert summary["successful"] == 0
    assert summary["failed"] == 1
    assert summary["failures"][0]["concept_id"] == "concept-1"
    assert cache_manager.calls == []


@pytest.mark.asyncio
async def test_validate_scores_returns_metrics():
    session = FakeSession(
        [
            FakeResult(single={"null_score_count": 0}),
            FakeResult(single={"out_of_range_count": 1}),
            FakeResult(single={"missing_components_count": 0}),
            FakeResult(
                single={
                    "total_concepts": 5,
                    "min_score": 0.2,
                    "max_score": 0.9,
                    "avg_score": 0.55,
                }
            ),
        ]
    )
    driver = FakeDriver(session)

    metrics = await validate_scores(driver)

    assert metrics["valid"] is False
    assert metrics["out_of_range"] == 1
    assert metrics["stats"]["total"] == 5
