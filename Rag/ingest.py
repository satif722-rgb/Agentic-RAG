#importing all essential lib.....
#renv\Scripts\activate
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os

#defining the path...

pdf_files=[
    {
        "path":"data\leave_policy.pdf",
        "document_type":"leave_policy",
        "file_name":"leave_policy.pdf"
    },
    {
        "path":"data\employee_handbook.pdf",
        "document_type":"employee_handbook",
        "file_name":"employee_handbook.pdf"
    },
    {
        "path":"data\hr_policy_manual.pdf",
        "document_type":"policy_manual",
        "file_name":"hr_policy_manual.pdf"
    }
]

#Data_path="data\leave_policy.pdf"
Vector_path="vector_store"
#Doc_type="leave_policy"
all_docs=[]
for pdf in pdf_files:
    loader=PyPDFLoader(pdf["path"])
    docs=loader.load()

    for doc in docs:
        doc.metadata["document_type"]=pdf["document_type"]
        doc.metadata["file_name"]=pdf["file_name"]
    all_docs.extend(docs)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)
chunks = splitter.split_documents(all_docs)

embeddings=HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    encode_kwargs={"normalize_embeddings":True}
)

db=FAISS.from_documents(chunks,embeddings)
db.save_local(Vector_path)

print("All pdf indexed successfully with metadata")





