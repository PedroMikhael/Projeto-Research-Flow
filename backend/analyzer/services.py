import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import requests
import tempfile
import re
from typing import Optional
from PyPDF2 import PdfReader
import urllib.parse

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# Configura a API do Google com a chave que está no .env
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Modelo Gemini padrão (pode ser sobrescrito por variável de ambiente GEMINI_MODEL)
# Model name constants for convenience
GEMINI_FLASH_2_0 = "gemini-2.0-flash"
GEMINI_FLASH_2_5 = "gemini-2.5-flash"
GEMINI_PRO_2_0 = "gemini-2.0-pro"
GEMINI_PRO_2_5 = "gemini-2.5-pro"

# Default model (can be overridden by environment variable GEMINI_MODEL)
MODEL_NAME = os.getenv("GEMINI_MODEL", GEMINI_PRO_2_5)

def extract_first_json(text: str) -> Optional[str]:
    """Extract the first balanced JSON object from text, ignoring braces inside strings."""
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None


def call_model(model, prompt_text: str, max_tokens: int = 4096) -> str:
    """Call the generative model with a safe kwargs fallback."""
    try:
        return model.generate_content(prompt_text, temperature=0, max_output_tokens=max_tokens).text
    except TypeError:
        return model.generate_content(prompt_text).text

def fetch_pdf_text_from_url(url: str) -> Optional[str]:
    """
    Baixa um PDF a partir de uma URL e tenta extrair o texto usando PyPDF2.
    Retorna None em caso de falha.
    """
    tmp_path = None
    try:
        resp = requests.get(url, stream=True, timeout=15)
        resp.raise_for_status()
        ctype = resp.headers.get('content-type', '')
        if 'text/html' in ctype.lower():
            html = resp.text
            m = re.search(r'href=["\']([^"\']+\.pdf)["\']', html, flags=re.IGNORECASE)
            if not m:
                m = re.search(r'href=["\']([^"\']+/pdf/[^"\']+\.pdf)["\']', html, flags=re.IGNORECASE)
            if m:
                resp = requests.get(urllib.parse.urljoin(url, m.group(1)), stream=True, timeout=15)
                resp.raise_for_status()
            elif '/abs/' in url:
                resp = requests.get(url.replace('/abs/', '/pdf/') + ('' if url.endswith('.pdf') else '.pdf'), stream=True, timeout=15)
                resp.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
            tmp_path = tmp.name

        reader = PdfReader(tmp_path)
        parts = [p.extract_text() or '' for p in reader.pages]
        return '\n\n'.join(parts).strip() or None
    except Exception as e:
        print(f"Erro ao obter/extrair PDF: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def summarize_article_with_gemini(article_text: str) -> dict:
    """
    Envia o texto do artigo para o Gemini e pede um resumo estruturado.

    Retorna um dicionário com as chaves: problem, methodology, results, conclusion
    Em caso de erro, retorna um dicionário com a chave 'error' e mensagem.
    """
    # Limpa/encaixa o prompt para que o modelo retorne apenas JSON
    prompt = f"""
    Você é um assistente que resume artigos acadêmicos. Sua tarefa é produzir
    um objeto JSON com as seguintes chaves obrigatórias: "problem", "methodology",
    "results", "conclusion". Cada valor deve ser um texto sucinto (1-4 sentenças).

    Regras estritas:
    - Retorne APENAS um objeto JSON válido (Com explicações, mais textos adicionais).
    - Mantenha a linguagem em português e seja objetivo.
    - Faça uma explicação completa e clara para cada seção.
    - Traga também detalhes específicos do artigo, como nomes de métodos, métricas e resultados numéricos.

    Artigo (trecho ou texto completo):
    """
    safe_text = article_text[:12000]
    full_prompt = f"{prompt}\n{safe_text}\n\nSua saída:"
    model = genai.GenerativeModel(MODEL_NAME)
    few_shot = '{"problem": "(2-4 sent.)", "methodology": "(2-4 sent.)", "results": "(2-4 sent.)", "conclusion": "(2-4 sent.)"}\n'
    raw = call_model(model, few_shot + "\n" + full_prompt)
    cleaned = (raw or '').replace('```json', '').replace('```', '').strip()
    try:
        data = json.loads(cleaned)
    except Exception:
        candidate = extract_first_json(cleaned)
        if not candidate:
            return {"error": "Resposta inválida do modelo de IA.", "raw": (raw or '')[:1000]}
        try:
            data = json.loads(candidate)
        except Exception:
            return {"error": "Resposta inválida do modelo de IA.", "raw": (raw or '')[:1000]}

    return {
        'problem': (data.get('problem') or '').strip(),
        'methodology': (data.get('methodology') or '').strip(),
        'results': (data.get('results') or '').strip(),
        'conclusion': (data.get('conclusion') or '').strip(),
    }
    

