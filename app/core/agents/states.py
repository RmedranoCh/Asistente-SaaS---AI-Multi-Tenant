from typing import TypedDict, Optional, List, Dict, Any


class EmailAgentState(TypedDict, total=False):
    company_id: str
    email_log_id: str

    sender: str
    subject: str
    body: str

    intent: Optional[str]
    rag_context: Optional[str]
    suggested_reply: Optional[str]

    requires_approval: bool
    actions_taken: List[Dict[str, Any]]

    tool_error: Optional[str]
