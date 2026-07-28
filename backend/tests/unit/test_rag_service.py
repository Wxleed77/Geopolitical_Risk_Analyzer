from app.services.rag_service import build_citation, find_relevant_case_studies


class FakeCase:
    """Stands in for a ConflictCase ORM row - avoids needing a real DB."""

    def __init__(self, id, name, a, b, outcome="Some outcome."):
        self.id = id
        self.name = name
        self.country_a_iso = a
        self.country_b_iso = b
        self.documented_outcome = outcome


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalars(self._items)


class FakeSession:
    def __init__(self, cases):
        self.cases = cases

    def execute(self, stmt):
        return FakeResult(self.cases)


def test_exact_conflict_match_ranks_highest():
    cases = [
        FakeCase(1, "USA-CHN Trade War", "USA", "CHN"),
        FakeCase(2, "Unrelated Conflict", "RUS", "UKR"),
    ]
    session = FakeSession(cases)
    result = find_relevant_case_studies(session, "USA", "CHN")
    assert len(result) == 1
    assert result[0].name == "USA-CHN Trade War"


def test_partial_overlap_still_matches():
    cases = [FakeCase(1, "USA-Iran Tension", "USA", "IRN")]
    session = FakeSession(cases)
    result = find_relevant_case_studies(session, "USA", "CHN")  # only USA overlaps
    assert len(result) == 1


def test_no_overlap_excluded():
    cases = [FakeCase(1, "Russia-Ukraine War", "RUS", "UKR")]
    session = FakeSession(cases)
    result = find_relevant_case_studies(session, "USA", "CHN")
    assert result == []


def test_exact_match_ranked_above_partial_match():
    cases = [
        FakeCase(1, "Partial Match", "USA", "IRN"),
        FakeCase(2, "Exact Match", "USA", "CHN"),
    ]
    session = FakeSession(cases)
    result = find_relevant_case_studies(session, "USA", "CHN", top_k=2)
    assert result[0].name == "Exact Match"
    assert result[1].name == "Partial Match"


def test_top_k_limits_results():
    cases = [FakeCase(i, f"Case {i}", "USA", "CHN") for i in range(5)]
    session = FakeSession(cases)
    result = find_relevant_case_studies(session, "USA", "CHN", top_k=2)
    assert len(result) == 2


def test_build_citation_truncates_snippet():
    case = FakeCase(1, "Test Case", "USA", "CHN", outcome="x" * 300)
    citation = build_citation(case)
    assert citation.source == "Test Case"
    assert citation.url == "internal://case_studies/1"
    assert len(citation.snippet) == 200
