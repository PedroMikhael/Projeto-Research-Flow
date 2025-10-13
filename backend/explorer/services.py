import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import requests

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# Configura a API do Google com a chave que está no .env
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_keywords_with_gemini(natural_language_query: str) -> str:
    """
    Usa a IA do Gemini para extrair os termos de busca de uma frase.
    """
    prompt = f"""
    Você é um processador de linguagem natural para um motor de busca acadêmico. Sua única função é converter uma consulta de usuário em uma string de palavras-chave otimizada para uma API de pesquisa como a do Semantic Scholar.

    Siga estas regras estritamente:
    1.  **Analise a Intenção:** Identifique os conceitos, tecnologias, substantivos e termos técnicos principais na consulta do usuário.
    2.  **Remova o Ruído:** Descarte completamente todos os elementos conversacionais.
    3.  **Mantenha a Essência:** Preserve apenas os termos que são cruciais para a busca.
    4.  **Formato de Saída Obrigatório:** A sua resposta DEVE SER um objeto JSON válido contendo uma única chave chamada "keywords". O valor dessa chave será a string com as palavras-chave processadas, em minúsculas e separadas por espaços. Não inclua NENHUM texto fora deste objeto JSON.

    Exemplos de Casos de Uso:
    -   **Consulta do Usuário:** "me encontre, por favor, artigos recentes sobre o impacto da inteligência artificial na economia do Brasil"
    -   **Sua Saída:** {{"keywords": "impacto inteligência artificial economia brasil"}}

    -   **Consulta do Usuário:** "história da computação quântica"
    -   **Sua Saída:** {{"keywords": "história computação quântica"}}

    Processe a seguinte consulta do usuário:
    **Consulta do Usuário:** "{natural_language_query}"
    **Sua Saída:**
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(cleaned_text)
        keywords = data['keywords']
        print(f"Keywords extraídas pelo Gemini (via JSON): '{keywords}'")
        return keywords
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"Erro ao processar resposta do Gemini: {e}. Usando fallback.")
        return natural_language_query.lower()

def search_articles_from_api(query: str):
    """
    Busca artigos na API do Semantic Scholar usando as palavras-chave fornecidas.
    """
    print(f"Buscando artigos REAIS no Semantic Scholar para: '{query}'")

    # Endereço base da API do Semantic Scholar
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Parâmetros da nossa busca
    params = {
        'query': query,
        'limit': 10,  # Quantos artigos queremos de volta? 10 é um bom número.
        'fields': 'title,authors,year,url,abstract,citationCount,journal' # Quais dados queremos de cada artigo?
    }

    try:
        # Faz a requisição GET para a API
        response = requests.get(base_url, params=params, timeout=10) # Timeout de 10 segundos
        response.raise_for_status()  # Lança um erro se a resposta for mal-sucedida (ex: 404, 500)

        data = response.json()

        # Formata a resposta da API para ser mais limpa e útil para o front-end
        results = []
        if data.get('data'):
            for item in data['data']:
                # Ignora artigos que não têm um resumo, pois eles não são muito úteis para nós
                if not item.get('abstract'):
                    continue

                results.append({
                    'title': item.get('title'),
                    'authors': [author['name'] for author in item.get('authors', [])],
                    'year': item.get('year'),
                    'url': item.get('url'),
                    'abstract': item.get('abstract'),
                    'citationCount': item.get('citationCount'),
                    'journal': item.get('journal', {}).get('name', 'N/A') # Tratamento para caso não tenha journal
                })
        return results

    except requests.exceptions.RequestException as e:
        print(f"Erro ao chamar a API do Semantic Scholar: {e}")
        # Se a API externa falhar, retornamos um erro claro para o front-end
        return {"error": "Falha ao se comunicar com a base de dados de artigos. Tente novamente mais tarde."}