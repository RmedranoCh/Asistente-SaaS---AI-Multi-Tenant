from langgraph.graph import StateGraph, END
from app.core.agents.states import EmailAgentState
from app.core.agents.nodes import (
    node_classify_email,
    node_enrich_rag,
    node_decision_and_draft,
    node_execute_actions,
)


def routing_workflow(state: EmailAgentState) -> str:
    if state.get("intent") == "Duda":
        return "go_to_rag"
    return "go_to_draft"


workflow = StateGraph(EmailAgentState)

workflow.add_node("classify", node_classify_email)
workflow.add_node("rag_enrich", node_enrich_rag)
workflow.add_node("decision_draft", node_decision_and_draft)
workflow.add_node("execute_actions", node_execute_actions)

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

email_cognitive_graph = workflow.compile()
