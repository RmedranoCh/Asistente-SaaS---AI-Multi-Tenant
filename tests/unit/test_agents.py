import pytest

from app.core.agents.graph import build_email_cognitive_graph, routing_workflow
from app.core.agents.nodes import (
    _extract_email_address,
    _extract_meeting_details,
    _safe_json,
    node_classify_email,
    node_decision_and_draft,
)


class TestSafeJson:
    def test_valid_json(self):
        assert _safe_json('{"intent": "Duda"}') == {"intent": "Duda"}

    def test_json_fenced_with_triple_backticks(self):
        raw = '```json\n{"intent": "Queja"}\n```'
        assert _safe_json(raw) == {"intent": "Queja"}

    def test_invalid_returns_empty_dict(self):
        assert _safe_json("no es json") == {}
        assert _safe_json("") == {}
        assert _safe_json(None) == {}


class TestExtractEmailAddress:
    def test_display_name_with_angle_brackets(self):
        assert _extract_email_address("Cliente Juan <juan@example.com>") == "juan@example.com"

    def test_plain_address(self):
        assert _extract_email_address("juan@example.com") == "juan@example.com"

    def test_empty(self):
        assert _extract_email_address("") == ""
        assert _extract_email_address(None) == ""


class TestExtractMeetingDetails:
    async def test_returns_none_when_no_meeting(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: '{"meeting": null}',
        )
        state = {"subject": "Hola", "body": "Solo saludo"}
        assert await _extract_meeting_details(state) is None

    async def test_parses_valid_meeting(self, monkeypatch):
        payload = (
            '{"meeting": true, "summary": "Demo", "description": "Demo producto", '
            '"start_iso": "2026-01-01T15:00:00Z", "duration_minutes": 30}'
        )
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: payload,
        )
        state = {"subject": "Cita", "body": "Viernes 3pm"}
        result = await _extract_meeting_details(state)
        assert result is not None
        assert result["summary"] == "Demo"
        assert result["start_iso"] == "2026-01-01T15:00:00Z"
        assert result["end_iso"] == "2026-01-01T15:30:00Z"

    async def test_returns_none_on_bad_dates(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: '{"meeting": {}, "start_iso": "fecha-invalida", "duration_minutes": 30}',
        )
        state = {"subject": "X", "body": "Y"}
        assert await _extract_meeting_details(state) is None


class TestClassifyEmail:
    def test_maps_valid_intent(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: '{"intent": "Reembolso"}',
        )
        state = node_classify_email({"subject": "S", "body": "Quiero reembolso"})
        assert state["intent"] == "Reembolso"

    def test_unknown_intent_falls_back_to_queja(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: '{"intent": "OtraCosa"}',
        )
        state = node_classify_email({"subject": "S", "body": "B"})
        assert state["intent"] == "Queja"

    def test_ai_failure_falls_back_to_queja(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: None,
        )
        state = node_classify_email({"subject": "S", "body": "B"})
        assert state["intent"] == "Queja"


class TestDecisionAndDraft:
    def test_refund_requires_approval(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: "Respuesta de ejemplo",
        )
        state = node_decision_and_draft(
            {"intent": "Reembolso", "sender": "a@b.c", "subject": "S", "body": "B"}
        )
        assert state["requires_approval"] is True
        assert state["suggested_reply"] == "Respuesta de ejemplo"

    def test_question_auto_send(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.agents.nodes._ai_generate",
            lambda *a, **k: "Respuesta",
        )
        state = node_decision_and_draft(
            {"intent": "Duda", "sender": "a@b.c", "subject": "S", "body": "B"}
        )
        assert state["requires_approval"] is False

    def test_ai_failure_sets_approval_and_error(self, monkeypatch):
        monkeypatch.setattr("app.core.agents.nodes._ai_generate", lambda *a, **k: None)
        state = node_decision_and_draft(
            {"intent": "Duda", "sender": "a@b.c", "subject": "S", "body": "B"}
        )
        assert state["requires_approval"] is True
        assert "draft_error" in (state.get("tool_error") or "")


class TestRoutingWorkflow:
    def test_duda_routes_to_rag(self):
        assert routing_workflow({"intent": "Duda"}) == "go_to_rag"

    @pytest.mark.parametrize("intent", ["Cita", "Reembolso", "Queja", None, ""])
    def test_others_route_to_draft(self, intent):
        assert routing_workflow({"intent": intent}) == "go_to_draft"


class TestGraphBuilder:
    async def test_question_flow_visits_expected_nodes(self):
        visited = []

        async def fake_classify(state):
            visited.append("classify")
            state["intent"] = "Duda"
            return state

        async def fake_enrich(state):
            visited.append("rag_enrich")
            state["rag_context"] = "contexto"
            return state

        async def fake_draft(state):
            visited.append("decision_draft")
            state["suggested_reply"] = "ok"
            state["requires_approval"] = False
            return state

        async def fake_execute(state):
            visited.append("execute_actions")
            state["actions_taken"] = []
            return state

        graph = build_email_cognitive_graph(
            node_classify=fake_classify,
            node_enrich=fake_enrich,
            node_draft=fake_draft,
            node_execute=fake_execute,
        )
        result = await graph.ainvoke({"subject": "S", "body": "B", "intent": None})
        assert visited == ["classify", "rag_enrich", "decision_draft", "execute_actions"]
        assert result["rag_context"] == "contexto"

    async def test_refund_flow_skips_rag(self):
        visited = []

        async def fake_classify(state):
            state["intent"] = "Reembolso"
            return state

        async def fake_enrich(state):
            visited.append("rag_enrich")
            state["rag_context"] = "X"
            return state

        async def fake_draft(state):
            state["suggested_reply"] = "ok"
            state["requires_approval"] = True
            return state

        async def fake_execute(state):
            state["actions_taken"] = []
            return state

        graph = build_email_cognitive_graph(
            node_classify=fake_classify,
            node_enrich=fake_enrich,
            node_draft=fake_draft,
            node_execute=fake_execute,
        )
        await graph.ainvoke({"subject": "S", "body": "B"})
        assert visited == []  # Reembolso no pasa por RAG
