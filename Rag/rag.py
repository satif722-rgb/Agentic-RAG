from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
#from langchain.chains import RetrievalQA
from .prompt import HR_PROMPT
from langchain_ollama import ChatOllama
#from logger import log_similarity

NO_ANSWER_PHRASE = "I don't have that information in the HR policies."

embeddings=HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    encode_kwargs={"normalize_embeddings":True}
    )

db=FAISS.load_local(
    "vector_store",
    embeddings,
    allow_dangerous_deserialization=True
)

llm = ChatOllama(model="llama3.2", temperature=0)

"""qa=RetrievalQA.from_chain_type(
    llm=llm,
    retriever=db.as_retriever(search_kwargs={"k":3}),
    return_source_documents=True,
    chain_type_kwargs={"prompt":HR_PROMPT}
)"""
SIMILARITY_THRESHOLD = {
    "leave_policy": 0.78,
    "policy_manual": 0.80,
    "employee_handbook": 0.88
}
def ask_hr(question: str) -> dict:
    print(">>> RAG RECEIVED QUESTION:", repr(question))
    """if not question.strip():
        return {
            "answer": "Please ask a valid HR-related question.",
            "sources": []
        }"""
    docs_with_scores = db.similarity_search_with_score(
        question,
        k=5
    )
    #call this function for log similarity to get best threshold value.
    #log_similarity(question, docs_with_scores)

    """ print("\nDEBUG SCORES:")
    for doc, score in docs_with_scores:
        print(f"{score:.3f} | {doc.metadata.get('file_name')} | {doc.page_content[:60]}")"""
    
    filtered = [
        (doc, score)
        for doc, score in docs_with_scores
        if score <= SIMILARITY_THRESHOLD.get(doc.metadata["document_type"],0.80)
    ]

    if not filtered:
        return{
            "answer":NO_ANSWER_PHRASE,
            "sources":[]
        }

    context = "\n\n".join(doc.page_content for doc, _ in filtered)
    prompt=HR_PROMPT.format(
        context=context,
        question=question
        )
    answer=llm.invoke(prompt).content.strip()
    sources=[]

    # STRICT check: show sources ONLY if answer is grounded
    if answer.startswith(NO_ANSWER_PHRASE):
    # Do NOT print sources
        pass
    else:
        seen = set()
        #print("\nSources:")
        for doc,_ in filtered:
            key = (doc.metadata.get("file_name"), doc.metadata.get("page"))
            if key not in seen:
                seen.add(key)
                sources.append(f"-{key[0]} (page{key[1]})")
                #print(f"- {key[0]} (page {key[1]})")
    return {
    "answer": answer,
    "sources": sources
    }
