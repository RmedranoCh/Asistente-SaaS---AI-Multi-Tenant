from langgraph.graph import END, StateGraph

from app.core.agents.nodes import (
    node_classify_email,
    node_decision_and_draft,
    node_enrich_rag,
    node_execute_actions,
)
from app.core.agents.states import EmailAgentState


def routing_workflow(state: EmailAgentState) -> str:
    if state.get("intent") == "Duda":
        return "go_to_rag"
    return "go_to_draft"


def build_email_cognitive_graph(
    node_classify=node_classify_email,
    node_enrich=node_enrich_rag,
    node_draft=node_decision_and_draft,
    node_execute=node_execute_actions,
):
    """Construye el grafo cognitivo del agente.

    Acepta implementaciones de nodos como parámetros para facilitar la
    inyección de dependencias en pruebas sin llamar a Gemini ni a RAG.
    """
    workflow = StateGraph(EmailAgentState)

    workflow.add_node("classify", node_classify)
    workflow.add_node("rag_enrich", node_enrich)
    workflow.add_node("decision_draft", node_draft)
    workflow.add_node("execute_actions", node_execute)

    workflow.set_entry_point("classify")

    workflow.add_conditional_edges(
        "classify",
        routing_workflow,
        {
            "go_to_rag": "rag_enrich",
            "go_to_draft": "decision_draft",
        },
    )

    workflow.add_edge("rag_enrich", "decision_draft")
    workflow.add_edge("decision_draft", "execute_actions")
    workflow.add_edge("execute_actions", END)

    return workflow.compile()


email_cognitive_graph = build_email_cognitive_graph()