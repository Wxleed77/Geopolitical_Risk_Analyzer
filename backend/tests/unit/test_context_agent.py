from app.agents.context_agent import extract_conflict_parties


class FakeLLMClient:
    def __init__(self, canned_response: str):
        self.canned_response = canned_response
        self.calls = []

    def complete(self, system, user, models=None):
        self.calls.append({"system": system, "user": user})
        return self.canned_response


def test_extracts_clean_json():
    llm = FakeLLMClient('{"country_a": "USA", "country_b": "CHN"}')
    a, b = extract_conflict_parties("Tension between the US and China over trade", llm)
    assert a == "USA"
    assert b == "CHN"


def test_strips_markdown_code_fences():
    llm = FakeLLMClient('```json\n{"country_a": "RUS", "country_b": "UKR"}\n```')
    a, b = extract_conflict_parties("Russia invaded Ukraine", llm)
    assert a == "RUS"
    assert b == "UKR"


def test_lowercases_input_gets_uppercased():
    llm = FakeLLMClient('{"country_a": "usa", "country_b": "irn"}')
    a, b = extract_conflict_parties("US-Iran tensions", llm)
    assert a == "USA"
    assert b == "IRN"


def test_null_response_returns_none_none():
    llm = FakeLLMClient('{"country_a": null, "country_b": null}')
    a, b = extract_conflict_parties("something vague and ambiguous", llm)
    assert a is None
    assert b is None


def test_malformed_json_falls_back_to_regex():
    llm = FakeLLMClient("I think this is about USA and CHN based on the context.")
    a, b = extract_conflict_parties("US vs China", llm)
    assert a == "USA"
    assert b == "CHN"


def test_completely_unparseable_returns_none_none():
    llm = FakeLLMClient("I'm not sure what countries are involved here.")
    a, b = extract_conflict_parties("something unclear", llm)
    assert a is None
    assert b is None


def test_single_code_found_is_insufficient():
    llm = FakeLLMClient("This involves USA somehow.")
    a, b = extract_conflict_parties("vague input", llm)
    assert a is None
    assert b is None
