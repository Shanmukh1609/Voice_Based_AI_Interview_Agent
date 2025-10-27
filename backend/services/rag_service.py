from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain.chains import create_retrieval_chain  
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
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
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", task_type="retrieval_document")
    
    # 3. Create a FAISS vector store
    try:
        vector_store = FAISS.from_documents(documents, embeddings)
    except Exception as e:
        print(f"Error creating FAISS vector store: {e}")
        print("This may be due to an invalid or missing Google API Key.")
        return None

    # 4. Create the LLM for the chain
    # --- MODIFIED: Corrected model name ---
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    
    # 5. Create the RAG chain
    # --- MODIFIED: Replaced deprecated RetrievalQA with create_retrieval_chain ---
    
    # This is the prompt template that will be "stuffed" with context
    prompt = ChatPromptTemplate.from_template(
        """Answer the following question based only on the provided context:

        <context>
        {context}
        </context>

        Question: {input}"""
    )

    # This chain handles "stuffing" the documents into the prompt
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    
    # This is the final chain that retrieves documents first, then passes to the QA chain
    rag_chain = create_retrieval_chain(
        vector_store.as_retriever(search_kwargs={"k": 2}),
        question_answer_chain
    )
    
    return rag_chain

def query_rag_chain(rag_chain, query: str) -> str:
    """
    Queries the RAG chain and returns the AI-generated answer.
    """
    if rag_chain is None:
        return ""
        
    try:
        # --- MODIFIED: Use new input/output keys ---
        
        # The input key is now "input"
        result = rag_chain.invoke({"input": query})
        
        # The AI's response is in the "answer" key
        return result.get("answer", "No answer could be generated.")
        
    except Exception as e:
        print(f"Error querying RAG chain: {e}")
        return ""