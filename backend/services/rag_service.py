from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.faiss import FAISS
from langchain.docstore.document import Document
from langchain.chains.retrieval_qa import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
import os

def create_rag_chain(company_facts: str):
    """
    Creates a RAG (Retrieval-Augmented Generation) chain from company facts.
    """
    if not company_facts:
        return None

    # 1. Split the company facts into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    # Wrap in Document objects, which LangChain expects
    documents = [Document(page_content=chunk) for chunk in text_splitter.split_text(company_facts)]
    
    if not documents:
        return None

    # 2. Create embeddings
    # This converts text chunks into numerical vectors
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", task_type="retrieval_document")
    
    # 3. Create a FAISS vector store
    # This is a local, in-memory vector database
    try:
        vector_store = FAISS.from_documents(documents, embeddings)
    except Exception as e:
        print(f"Error creating FAISS vector store: {e}")
        print("This may be due to an invalid or missing Google API Key.")
        return None

    # 4. Create the LLM for the chain
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-09-2025", temperature=0.3)
    
    # 5. Create the RAG chain
    # "stuff" means it will "stuff" all retrieved documents into the prompt
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_kwargs={"k": 2}),
        return_source_documents=True
    )
    
    return rag_chain

def query_rag_chain(rag_chain, query: str) -> str:
    """
    Queries the RAG chain and returns a consolidated answer.
    """
    if rag_chain is None:
        return ""
        
    try:
        result = rag_chain.invoke({"query": query})
        # Combine the content of the source documents into a single string
        contexts = [doc.page_content for doc in result.get("source_documents", [])]
        return "\n---\n".join(contexts)
        
    except Exception as e:
        print(f"Error querying RAG chain: {e}")
        return ""
