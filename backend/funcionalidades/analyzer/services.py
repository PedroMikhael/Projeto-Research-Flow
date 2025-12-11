import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import requests
import tempfile
import re
from typing import Optional, List, Dict
from PyPDF2 import PdfReader
import urllib.parse
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "problem": {"type": "STRING"},
        "methodology": {"type": "STRING"},
        "results": {"type": "STRING"},
        "conclusion": {"type": "STRING"},
    },
    "required": ["problem", "methodology", "results", "conclusion"],
}

def extract_first_json(text: str) -> Optional[str]:
    """Helper de fallback para extrair JSON de texto sujo"""
    start = text.find('{')
    if start == -1: return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if esc: esc = False; continue
        if ch == '\\': esc = True; continue
        if ch == '"': in_str = not in_str; continue
        if in_str: continue
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: return text[start:i+1]
    return None

def call_model_structured(model, prompt_text: str, schema: dict) -> str:
    """
    Função especializada para chamadas com Schema Estruturado.
    Garante que o retorno obedeça ao formato JSON definido.
    """
    config = {
        "max_output_tokens": 8192, # Aumentei para garantir resumos longos se necessário
        "temperature": 0.2,
        "response_mime_type": "application/json",
        "response_schema": schema
    }

    try:
        response = model.generate_content(prompt_text, generation_config=config)
        return response.text
    except Exception as e:
        print(f"Erro na chamada do modelo: {e}")
        return ""

def extract_pdf_text_from_file(file_input) -> Optional[str]:
    try:
        reader = PdfReader(file_input)
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        full_text = '\n\n'.join(parts).strip()
        return full_text or None
    except Exception as e:
        print(f"Erro ao ler/extrair PDF do arquivo: {e}")
        return None

def get_wayback_machine_url(target_url: str) -> Optional[str]:
    print(f"Tentando resgatar via Wayback Machine: {target_url}")
    try:
        api_url = f"http://archive.org/wayback/available?url={target_url}"
        resp = requests.get(api_url, timeout=10)
        data = resp.json()
        if 'archived_snapshots' in data and 'closest' in data['archived_snapshots']:
            snapshot_url = data['archived_snapshots']['closest']['url']
            print(f"Cópia encontrada no Wayback Machine: {snapshot_url}")
            return snapshot_url
        else:
            print("Nenhuma cópia encontrada no Wayback Machine.")
            return None
    except Exception as e:
        print(f"Erro ao consultar Wayback Machine: {e}")
        return None

def resolve_semantic_scholar_url(url: str) -> Optional[str]:
    match = re.search(r"semanticscholar\.org/paper/.*?([a-fA-F0-9]{40})", url)
    if not match:
        match = re.search(r"semanticscholar\.org/paper/([a-fA-F0-9]{40})", url)
    
    if match:
        paper_id = match.group(1)
        print(f"Detecado Semantic Scholar ID: {paper_id}. Buscando PDF via API...")
        api_key = os.getenv("SEMANTIC_API_KEY")
        headers = {'x-api-key': api_key} if api_key else {}
        try:
            api_url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=openAccessPdf,url"
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                open_access = data.get('openAccessPdf')
                if open_access and open_access.get('url'):
                    pdf_url = open_access.get('url')
                    print(f"PDF encontrado via API: {pdf_url}")
                    return pdf_url
        except Exception as e:
            print(f"Erro ao resolver Semantic Scholar URL: {e}")
    return None

def fetch_pdf_text_from_url(url: str) -> Optional[str]:
    tmp_path = None
    target_url = url
    resolved_url = resolve_semantic_scholar_url(url)
    if resolved_url:
        target_url = resolved_url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        print(f"Baixando (Tentativa 1): {target_url}")
        resp = requests.get(target_url, headers=headers, stream=True, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Falha no download direto: {e}")
        print("Ativando protocolo de resgate (Wayback Machine)...")
        wayback_url = get_wayback_machine_url(target_url)
        if wayback_url:
            try:
                print(f"Baixando do Arquivo: {wayback_url}")
                resp = requests.get(wayback_url, headers=headers, stream=True, timeout=30)
                resp.raise_for_status()
            except Exception as wb_e:
                print(f"Falha também no Wayback Machine: {wb_e}")
                return None
        else:
            print("Sem backup disponível.")
            return None

    try:
        content_type = resp.headers.get('content-type', '').lower()
        final_url = resp.url

        if 'application/pdf' not in content_type:
            print(f"Conteúdo é HTML ({content_type}). Procurando link do PDF na página...")
            html = resp.text
            
            m_meta = re.search(r'<meta\s+name=["\']citation_pdf_url["\']\s+content=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
            pdf_link = None
            if m_meta:
                pdf_link = m_meta.group(1)
            
            if not pdf_link:
                m_href = re.search(r'href=["\']([^"\']+\.pdf)["\']', html, flags=re.IGNORECASE)
                if m_href:
                    pdf_link = m_href.group(1)
                else:
                    m_view = re.search(r'href=["\']([^"\']+/article/view/[^"\']+/[\d]+)["\']', html, flags=re.IGNORECASE) 
                    if not m_view:
                        m_view = re.search(r'href=["\']([^"\']+/pdf/[^"\']+)["\']', html, flags=re.IGNORECASE)
                    if m_view:
                        pdf_link = m_view.group(1)

            if pdf_link:
                pdf_link = urllib.parse.urljoin(final_url, pdf_link)
                print(f"Redirecionando para o PDF real: {pdf_link}")
                resp = requests.get(pdf_link, headers=headers, stream=True, timeout=20)
                resp.raise_for_status()
            else:
                print("Não foi possível encontrar um link de PDF nesta página HTML.")
                return None

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
            tmp_path = tmp.name

        try:
            reader = PdfReader(tmp_path)
            parts = []
            for p in reader.pages:
                text = p.extract_text()
                if text:
                    parts.append(text)
            
            full_text = '\n\n'.join(parts).strip()
            if not full_text:
                return None
            return full_text
            
        except Exception as e:
            print(f"Erro ao ler o arquivo PDF baixado: {e}")
            return None

    except Exception as e:
        print(f"Erro ao obter/extrair PDF: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass

def extract_text_content(input_value: str, is_url: bool = False) -> dict:
    text = ""
    if is_url:
        text = fetch_pdf_text_from_url(input_value)
        if not text:
            return {"error": "Falha ao baixar/ler o PDF."}
    else:
        text = input_value or ''

    if not text.strip():
        return {"error": "Texto vazio."}
    return {"text": text}

def extract_text_from_file_obj(file_obj) -> dict:
    try:
        reader = PdfReader(file_obj)
        parts = [p.extract_text() or '' for p in reader.pages]
        text = '\n\n'.join(parts).strip()
        if not text:
             return {"error": "Não foi possível extrair texto do arquivo PDF."}
        return {"text": text}
    except Exception as e:
        return {"error": f"Erro ao ler arquivo: {str(e)}"}

def chat_with_context(context_text: str, messages: List[Dict[str, str]]) -> dict:
    limit_chars = 100000
    
    prompt_system = f"""
    Você é um assistente acadêmico especialista.
    Use o seguinte texto extraído de um artigo científico como sua única fonte de verdade para responder à pergunta do usuário.
    
    --- INÍCIO DO ARTIGO ---
    {context_text[:limit_chars]}
    --- FIM DO ARTIGO ---

    Instruções:
    1. Responda de forma direta, educada e técnica.
    2. Se a resposta não estiver no contexto, diga que o artigo não menciona isso.
    3. Use formatação Markdown para deixar a resposta clara.
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash") # Usando um modelo estável
        
        # 1. Constrói o histórico da conversa para dar memória à IA
        chat_history_str = ""
        for msg in messages:
             # Acessa com get() para evitar erros
             role = "Usuário" if msg.get('role') == 'user' else "Assistente"
             chat_history_str += f"{role}: {msg.get('content')}\n"
        
        # 2. Pega a última pergunta do usuário de forma segura
        last_user_msg = messages[-1].get('content') if messages and messages[-1].get('role') == 'user' else "Qual é o principal tema deste documento?"
        
        full_prompt = f"{prompt_system}\n\nHistórico da Conversa:\n{chat_history_str}\n\nUsuário: {last_user_msg}\nResposta:"
        
        response = model.generate_content(full_prompt)
        return {"response": response.text}
    except Exception as e:
        # Retorna o erro exato para debugging
        return {"error": str(e)}

def summarize_article_with_gemini(article_text: str, natural_language_query: Optional[str] = None) -> dict:
    
    # 1. Instrução de foco
    instruction_block = ""
    if natural_language_query and natural_language_query.strip():
        instruction_block = f"""
        USER PRIORITY INSTRUCTION: "{natural_language_query}".
        
        You should filter and adapt the fields below to focus on this query.
        If the article does not answer the query, please state this in the conclusion.
        """
    else:
        instruction_block = "Generate a comprehensive technical summary."

    # 2. Prompt principal
    prompt = f"""
    You are an expert in scientific synthesis. Analyze the provided text and fill in the requested fields.
    
    {instruction_block}
    
    Please fill in the fields in Brazilian Portuguese in detail.
    Article Text:
    {article_text[:60000]} 
    """
    
    model = genai.GenerativeModel(MODEL_NAME)
    
    # CHAMADA COM SCHEMA REFORÇADO
    raw = call_model_structured(model, prompt, schema=SUMMARY_SCHEMA)
    
    if not raw:
        return {"error": "O modelo retornou uma resposta vazia."}

    try:
        # Como usamos response_schema, o output é garantido ser JSON válido.
        # Não precisamos de regex para limpar ```json
        data = json.loads(raw)
    except Exception as e:
        # Fallback extremamente raro se a API falhar no schema
        print(f"Erro no parse direto (raro com schema): {e}")
        cleaned = raw.replace('```json', '').replace('```', '').strip()
        try:
            data = json.loads(cleaned)
        except:
             return {"error": "Falha crítica no processamento do JSON.", "raw": raw[:500]}

    def _normalize_field(v):
        if v is None: return ''
        return str(v).strip()

    return {
        'problem': _normalize_field(data.get('problem')),
        'methodology': _normalize_field(data.get('methodology')),
        'results': _normalize_field(data.get('results')),
        'conclusion': _normalize_field(data.get('conclusion')),
    }

def summarize_article(input_value: str, is_url: bool = False, natural_language_query: Optional[str] = None) -> dict:
    if is_url:
        text = fetch_pdf_text_from_url(input_value)
        if not text:
            return {"error": "Falha ao baixar/ler o PDF."}
    else:
        text = input_value or ''
    
    if not text.strip():
        return {"error": "Texto vazio para resumir."}
    
    # Repassa a query para a função do Gemini
    return summarize_article_with_gemini(text, natural_language_query=natural_language_query)