from typing import TypedDict, Optional, Literal,Annotated
from langgraph.channels import LastValue
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from tools.tools import hr_policy_lookup,get_leave_balance
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver

policy_extractor_llm = ChatOllama(
    model="llama3.2",
    temperature=0
)
class HRState(TypedDict):
    
    question: Annotated[str, LastValue]

    employee_id: Optional[str]
    leave_type: Optional[str]

    route: Optional[str]

    policy_question: Optional[str]
    policy_answer: Optional[str]
    personal_answer: Optional[str]
    final_answer: Optional[str]


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
def detect_route(question: str) -> str:
    q = question.lower()

    policy_keywords = ["policy", "rule", "allowed", "entitled"]
    personal_keywords = ["my", "i have", "balance", "remaining"]

    is_policy = any(k in q for k in policy_keywords)
    is_personal = any(k in q for k in personal_keywords)

    if is_policy and is_personal:
        return "mixed"
    if is_personal:
        return "personal"
    return "policy"


def router_node(state: HRState):
    question = state["question"]

    updates = {}

    # 🔥 Clear previous answers every new turn
    updates["policy_answer"] = None
    updates["personal_answer"] = None

    # Extract employee ID
    extracted_id = extract_employee_id(question)
    if extracted_id:
        updates["employee_id"] = extracted_id

    # Extract leave type
    extracted_leave = extract_leave_type(question)
    if extracted_leave:
        updates["leave_type"] = extracted_leave

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



def composer_node(state: HRState):
    policy = state.get("policy_answer")
    personal = state.get("personal_answer")

    if policy and personal:
        final = f"{policy}\n\n{personal}"

    elif policy:
        final = policy

    elif personal:
        final = personal

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





def build_hr_graph():
    graph = StateGraph(HRState)

    graph.add_node("router", router_node)
    graph.add_node("policy_node", policy_node)
    graph.add_node("personal_node", personal_node)
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

    graph.add_edge("composer", END)

    memory=MemorySaver()
    return graph.compile(checkpointer=memory)