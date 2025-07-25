from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi import FastAPI
from typing import List
import fitz 
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATABASE_FILE = "documents.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    content = Column(Text)


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="API teste clinica tatiana",
    description="Uma API para buscar conteúdo em documentos PDF.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

class SearchRequest(BaseModel):
    query: str

class SearchResultItem(BaseModel):
    """
    Modelo para um item de resultado da busca.
    """
    filename: str
    snippet: str

# Função para extrair texto de um arquivo PDF
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrai texto de um arquivo PDF usando PyMuPDF (fitz).
    """
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Erro ao extrair texto do PDF {pdf_path}: {e}")
    return text

# Função para carregar documentos no banco de dados
def load_documents_to_db(document_paths: List[str]):
    """
    Carrega o conteúdo dos documentos PDF no banco de dados.
    """
    db = SessionLocal()
    try:
        for doc_path in document_paths:
            filename = os.path.basename(doc_path)
            # Verifica se o documento já existe no banco de dados
            existing_doc = db.query(Document).filter(Document.filename == filename).first()
            if not existing_doc:
                print(f"Processando arquivo: {filename}")
                content = extract_text_from_pdf(doc_path)
                new_doc = Document(filename=filename, content=content)
                db.add(new_doc)
            else:
                print(f"Documento {filename} já existe no banco de dados. Pulando.")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro ao carregar documentos no banco de dados: {e}")
    finally:
        db.close()

DOCUMENT_PATHS = [
    "PDFs/TABELA DE PREÇOS ATUALIZADA (1).pdf",
    "PDFs/MANUAL DE ATENDIMENTO VERSÃO 02 DRIVE (1).pdf",
    "PDFs/CONVÊNIOS versão2.pdf"
]
