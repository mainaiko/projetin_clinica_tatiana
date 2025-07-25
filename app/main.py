import os
from fastapi import HTTPException
from typing import List
import re
from base import DOCUMENT_PATHS, SessionLocal, Document, app, SearchRequest, SearchResultItem, load_documents_to_db


# Carrega os documentos no banco de dados ao iniciar a aplicação
@app.on_event("startup")
async def startup_event():
    """
    Evento de inicialização para carregar documentos no banco de dados.
    """
    # Verifica se os arquivos existem antes de tentar carregá-los
    valid_document_paths = [p for p in DOCUMENT_PATHS if os.path.exists(p)]
    if not valid_document_paths:
        print("Nenhum arquivo PDF encontrado nos caminhos especificados. Certifique-se de que os arquivos estão na mesma pasta que o script ou forneça os caminhos corretos.")
    else:
        load_documents_to_db(valid_document_paths)

@app.get("/")
async def read_root():
    """
    Endpoint raiz da API.
    """
    return {"message": "Bem-vindo à API de Busca de Documentos. Use /search para buscar."}

@app.post("/search", response_model=List[SearchResultItem])
async def search_documents(request: SearchRequest):
    db = SessionLocal()
    results = []
    try:
        query_lower = request.query.lower()
        # Busca em todos os documentos onde o conteúdo contém a query
        documents = db.query(Document).filter(Document.content.ilike(f"%{query_lower}%")).all()

        for doc in documents:
            filename_lower = doc.filename.lower()
            
            # Define os comprimentos padrão do snippet
            chars_before = 100
            chars_after = 300

            # Lógica específica para a TABELA DE PREÇOS ATUALIZADA
            if "tabela de preços atualizada (1).pdf" in filename_lower:
                lines = doc.content.split('\n')
                table_header_line = ""
                table_data_line = ""
                
                # Procura pelo cabeçalho da tabela de ultrassom
                for line in lines:
                    if "tabela de preços ultrassom" in line.lower():
                        table_header_line = line.strip()
                        break

                # Procura pela linha de dados que contém a palavra-chave e números (preços)
                for line in lines:
                    if query_lower in line.lower() and re.search(r'\b\d+\b', line):
                        table_data_line = line.strip()
                        break
                
                if table_data_line: # Se encontrou a linha de dados, formata
                    # Se encontrou o cabeçalho, inclui-o. Caso contrário, apenas a linha de dados.
                    full_table_block = f"{table_header_line}\n{table_data_line}" if table_header_line else table_data_line
                    results.append(SearchResultItem(filename=doc.filename, snippet=full_table_block))
                    continue # Pula para o próximo documento, já que a tabela foi formatada
            
            # Lógica específica para CONVÊNIOS versão2.pdf
            elif "convênios versão2.pdf" in filename_lower:
                chars_before = 300
                chars_after = 300
            
            # Lógica padrão para MANUAL DE ATENDIMENTO e outros documentos,
            # ou para TABELA DE PREÇOS se a formatação de tabela não se aplicar
            matches = list(re.finditer(re.escape(request.query), doc.content, re.IGNORECASE))
            for match in matches:
                start_index = max(0, match.start() - chars_before)
                end_index = min(len(doc.content), match.end() + chars_after)
                
                snippet = doc.content[start_index:end_index]
                
                if start_index > 0 and doc.content[start_index-1] not in ['\n', '\r']:
                    snippet = "..." + snippet
                if end_index < len(doc.content) and doc.content[end_index] not in ['\n', '\r']:
                    snippet = snippet + "..."

                results.append(SearchResultItem(filename=doc.filename, snippet=snippet.strip()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar documentos: {e}")
    finally:
        db.close()
    return results
