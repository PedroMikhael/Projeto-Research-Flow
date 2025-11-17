from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Importe as duas funções do nosso módulo de serviços
from explorer.services import extract_keywords_with_gemini, search_articles_from_api

# Esta view já existe, você só precisa garantir que o conteúdo dela
# esteja igual ao abaixo
@api_view(['GET'])
def get_status(request):
    """
    Um endpoint simples para verificar se a API está online.
    """
    return Response({"status": "ok", "message": "Backend is running!"})

# SUBSTITUA A VERSÃO ANTIGA DESTA VIEW PELA NOVA ABAIXO
@api_view(['POST'])
def search_articles_view(request):
    """
    Recebe a query do frontend + filtros e retorna artigos no formato correto.
    """

    natural_query = request.data.get("query", "").strip()
    if not natural_query:
        return Response({
            "success": False,
            "message": "Nenhuma consulta foi enviada.",
            "articles": []
        }, status=400)

    # filtros recebidos do frontend
    sort_by = request.data.get("sort_by", "default")
    year_from = request.data.get("year_from", None)
    year_to = request.data.get("year_to", None)
    offset = request.data.get("offset", 0)
    is_open_access = request.data.get("is_open_access", False)

    # 1. Extrai keywords com o Gemini
    keywords = extract_keywords_with_gemini(natural_query)

    # 2. Busca artigos
    articles = search_articles_from_api(
        query=keywords,
        sort_by=sort_by,
        year_from=year_from,
        year_to=year_to,
        offset=offset,
        is_open_access=is_open_access
    )

    # Se a API falhar, já tratamos
    if isinstance(articles, dict) and articles.get("error"):
        return Response({
            "success": False,
            "message": "Erro ao consultar a base de artigos.",
            "articles": []
        }, status=500)

    # 3. Resposta no formato esperado pelo frontend
    return Response({
        "success": True,
        "message": f"Resultados encontrados para: {natural_query}",
        "articles": articles  # já é uma lista com até 25 itens
    })
