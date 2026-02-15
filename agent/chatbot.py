from typing import TypedDict, Optional, Literal,Annotated
from langgraph.channels import LastValue
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from tools.tools import hr_policy_lookup,get_leave_balance
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
import sqlite3

policy_extractor_llm = ChatOllama(
    model="llama3.2",
    temperature=0
)
class HRState(TypedDict):

    question: Annotated[str, LastValue]

    employee_id: Optional[str]
    leave_type: Optional[str]
    days: Optional[int] 

    route: Optional[str]

    policy_question: Optional[str]
    policy_answer: Optional[str]
    personal_answer: Optional[str]
    apply_answer: Optional[str] 
    final_answer: Optional[str]
    history_answer: Optional[str]




llm=ChatOllama(model="llama3.2")
policy_extractor_llm = ChatOllama(
    model="llama3.2",
    temperature=0
)

policy_extractor_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """
You are an information extraction system.

TASK:
Extract ONE clean HR POLICY QUESTION from the user input.

STRICT RULES:
- Output MUST be a single interrogative sentence
- Output MUST start with "What is"
- Output MUST end with "?"
- Do NOT answer the question
- Do NOT include explanations
- Do NOT include personal data
- Do NOT include leave balances
- If the policy is about sick leave, say "sick leave policy"
- If casual leave, say "casual leave policy"

EXAMPLES:
Input: "How many sick leaves do I have and what does policy say?"
Output: "What is the sick leave policy?"

Input: "Tell me my casual leave balance and rules"
Output: "What is the casual leave policy?"
"""),
    ("human", "{question}")
])


router_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """
You are an HR query classifier.

Classify the user's question into exactly ONE category:

- policy   → HR rules, policies, benefits, guidelines
- personal → employee-specific data (leave balance, records)
- mixed    → both policy AND personal data

Respond with ONLY ONE WORD:
policy OR personal OR mixed
"""),
    ("human", "{question}")
])

def extract_days(text: str):
    match = re.search(r"\b(\d+)\s*day", text.lower())
    return int(match.group(1)) if match else None


def detect_route(question: str) -> str:
    q = question.lower()

    if "apply" in q:
        return "apply"
    
    if "history" in q:
        return "history"

    if "balance" in q or "how many" in q:
        return "personal"

    if "policy" in q or "rule" in q:
        return "policy"

    return "policy"



def router_node(state: HRState):
    question = state["question"]

    updates = {}

    # RESET all previous outputs
    updates["policy_answer"] = None
    updates["personal_answer"] = None
    updates["apply_answer"] = None  # ✅ VERY IMPORTANT

    # Extract employee ID
    extracted_id = extract_employee_id(question)
    if extracted_id:
        updates["employee_id"] = extracted_id

    # Extract leave type
    extracted_leave = extract_leave_type(question)
    if extracted_leave:
        updates["leave_type"] = extracted_leave

    # Extract days
    extracted_days = extract_days(question)
    if extracted_days:
        updates["days"] = extracted_days
    else:
        updates["days"] = None   # ✅ reset days

    route = detect_route(question)
    updates["route"] = route

    return updates


def extract_leave_type(text: str):
    text = text.lower()

    if "medical" in text or "sick" in text:
        return "medical"

    if "casual" in text:
        return "casual"

    if "earned" in text:
        return "earned"

    return None

def extract_policy_question_llm(question: str) -> str:
    chain = policy_extractor_prompt | policy_extractor_llm
    response = chain.invoke({"question": question})
    extracted = response.content.strip()

    if not extracted.lower().startswith("what is") or not extracted.endswith("?"):
        raise ValueError(
            f"Invalid policy question extracted: {extracted}"
        )

    return extracted


def policy_node(state: HRState):
    if state["route"] == "mixed":
        policy_q = extract_policy_question_llm(state["question"])
        policy_q = normalize_policy_question(policy_q)
    else:
        policy_q = state["question"]

    normalized_question = (
        "This is an HR policy question.\n"
        f"Question: {policy_q}"
    )

    #print(">>> RAG RECEIVED QUESTION:", repr(normalized_question))

    result = hr_policy_lookup.invoke(
        {"question": normalized_question}
    )

    if isinstance(result, dict):
        answer = result.get("answer")
    else:
        answer = result

    return {
        "policy_question": policy_q,
        "policy_answer": answer
    }

def can_call_personal_tool(state) -> bool:
    return bool(state.get("employee_id") and state.get("leave_type"))


def personal_node(state: HRState):
    employee_id = state.get("employee_id")
    leave_type = state.get("leave_type")

    if not employee_id:
        return {
            "personal_answer": "Please share your employee ID so I can check your leave balance."
        }

    if not leave_type:
        return {
            "personal_answer": "Please tell me which leave type (medical, casual, earned) you'd like to check."
        }

    answer = get_leave_balance.invoke({
        "employee_id": employee_id,
        "leave_type": leave_type
    })

    return {"personal_answer": answer}


def apply_node(state: HRState):
    employee_id = state.get("employee_id")
    leave_type = state.get("leave_type")
    days = state.get("days")

    if not employee_id:
        return {
            "apply_answer": "Please provide your employee ID (e.g., EMP101)."
        }

    if not leave_type:
        return {
            "apply_answer": "Please specify leave type (medical, casual, earned)."
        }

    if not days:
        return {
            "apply_answer": "Please specify number of days."
        }

    leave_type = normalize_db_leave_type(leave_type)

    result = apply_leave_action(employee_id, leave_type, days)

    if isinstance(result, dict):
        message = result.get("message", str(result))
    else:
        message = str(result)

    return {"apply_answer": message}

def history_node(state: HRState):
    employee_id = state.get("employee_id")

    if not employee_id:
        return {
            "history_answer": "Please provide your employee ID to view leave history."
        }

    conn = sqlite3.connect("db/hr.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT leave_type, days, status, applied_on
        FROM leave_applications
        WHERE employee_id=?
        ORDER BY applied_on DESC
        """,
        (employee_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"history_answer": "No leave applications found."}

    history_text = "Your Leave History:\n\n"

    for leave_type, days, status, date in rows:
        history_text += f"- {leave_type} | {days} days | {status} | {date}\n"

    return {"history_answer": history_text}


def composer_node(state: HRState):
    policy = state.get("policy_answer")
    personal = state.get("personal_answer")
    apply_answer = state.get("apply_answer")
    history = state.get("history_answer")

    if apply_answer:
        final = apply_answer

    elif apply_answer and history:
        final=f"{apply_answer}\n\n{history}"

    elif policy and personal:
        final = f"{policy}\n\n{personal}"

    elif policy:
        final = policy

    elif personal:
        final = personal
    
    elif history:
        final = history

    else:
        final = "I'm not sure how to help with that."

    return {"final_answer": final}


def normalize_policy_question(question: str) -> str:
    """
    Normalize user policy questions to match HR document terminology.
    """
    q = question.lower()

    if "sick leave" in q:
        return "What is the medical leave policy?"

    if "medical leave" in q:
        return "What is the medical leave policy?"

    if "casual leave" in q:
        return "What is the casual leave policy?"

    if "earned leave" in q or "el" in q:
        return "What is the earned leave policy?"

    # fallback: return original question
    return question

def normalize_db_leave_type(leave_type: str) -> str:
    lt = leave_type.lower()

    if lt in ["sick", "medical"]:
        return "medical"

    if lt == "casual":
        return "casual"

    if lt in ["earned", "el"]:
        return "earned"

    return lt

import re

def extract_employee_id(text: str):
    match = re.search(r"\bEMP\d+\b", text.upper())
    return match.group(0) if match else None

import requests
def apply_leave_action(employee_id, leave_type, days):
    res = requests.post("http://localhost:8000/apply-leave", json={
       "employee_id": employee_id,
       "leave_type": leave_type,
       "days": days
    })
    return res.json()



def build_hr_graph():
    graph = StateGraph(HRState)

    graph.add_node("router", router_node)
    graph.add_node("policy_node", policy_node)
    graph.add_node("personal_node", personal_node)
    graph.add_node("apply_node", apply_node)
    graph.add_node("history_node", history_node)
    graph.add_node("composer", composer_node)

    graph.set_entry_point("router")

    # Routing
    graph.add_conditional_edges(
    "router",
    lambda state: state["route"],
    {
        "policy": "policy_node",
        "personal": "personal_node",
        "mixed": "policy_node",
        "apply": "apply_node",
        "history": "history_node",
    }
)



    graph.add_conditional_edges(
    "policy_node",
    lambda state: state["route"],
    {
        "policy": "composer",
        "mixed": "personal_node",
    }
)

    graph.add_edge("personal_node", "composer")
    graph.add_edge("apply_node", "composer")
    graph.add_edge("history_node", "composer")
    graph.add_edge("composer", END)

    memory=MemorySaver()
    return graph.compile(checkpointer=memory)