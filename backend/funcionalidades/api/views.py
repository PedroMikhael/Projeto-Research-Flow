from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from pathlib import Path
import os
from django.http import FileResponse
import mimetypes
from django.http import HttpResponse, Http404
from pathlib import Path

# Importa TODOS os serializers
from .serializers import (
    SearchQuerySerializer, 
    ApiResponseSerializer,
    SummarizeInputSerializer, # Mantido para compatibilidade se necessário
    SummarizeJsonInputSerializer, 
    SummarizeFormInputSerializer,
    SummarizeOutputSerializer,
    ExtractTextOutputSerializer,
    ChatInputSerializer,
    ChatOutputSerializer,
    FormatTextSerializer,
    FormatTextOutputSerializer
)

# Importa a lógica de CADA app separado
from explorer.services import extract_keywords_with_gemini, search_articles_from_api
from analyzer.services import summarize_article, extract_text_content, extract_text_from_file_obj, chat_with_context
from writer.services import format_text_with_gemini, extract_text_from_file

@extend_schema(exclude=True)
@api_view(['GET'])
def get_status(request):
    """ Um endpoint simples para verificar se a API está online. """
    return Response({"status": "ok", "message": "Backend is running!"})

@extend_schema(
    summary="Busca Artigos com IA",
    description="Recebe uma query de busca, usa IA para otimizá-la e retorna os artigos mais relevantes com filtros.",
    request=SearchQuerySerializer,
    responses={
        200: ApiResponseSerializer,
        400: {"description": "Erro de requisição."}
    }
)
@api_view(['POST'])
def search_articles_view(request):
    serializer = SearchQuerySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data
    
    # 1. Processa a query com IA
    keywords = extract_keywords_with_gemini(validated_data['query'])
    
    # 2. Busca no Semantic Scholar com todos os filtros
    articles = search_articles_from_api(
        query=keywords,
        sort_by=validated_data['sort_by'],
        year_from=validated_data.get('year_from'),
        year_to=validated_data.get('year_to'),
        offset=validated_data['offset'],
        is_open_access=validated_data['is_open_access']
    )

    if "error" in articles:
        return Response({
            "success": False,
            "message": "Puxa, tive um problema para me conectar à base de dados. Tente novamente.",
            "articles": []
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    if len(articles) > 0:
        return Response({
            "success": True,
            "message": f"Encontrei {len(articles)} artigos excelentes para você!",
            "articles": articles
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "success": True,
            "message": "Puxa, não encontrei artigos com esses filtros.",
            "articles": []
        }, status=status.HTTP_200_OK)


# --- NOVAS ROTAS DE RESUMO E CHAT ---

# Helper para resposta de resumo
def _handle_summarize_response(result):
    if "error" in result:
        if "Falha ao ler" in result.get("error", "") or "Falha ao baixar" in result.get("error", ""):
             return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(result, status=status.HTTP_200_OK)

@extend_schema(
    summary="[JSON] Resume Artigo",
    request=SummarizeJsonInputSerializer,
    responses={200: SummarizeOutputSerializer}
)
@api_view(['POST'])
@parser_classes([JSONParser])
def summarize_article_json_view(request):
    serializer = SummarizeJsonInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    input_val = serializer.validated_data['input_value']
    is_url_val = serializer.validated_data['is_url']
    query = serializer.validated_data.get('user_query')
    
    result = summarize_article(
        input_value=input_val, 
        is_url=is_url_val, 
        natural_language_query=query
    )
    
    return _handle_summarize_response(result)

@extend_schema(
    summary="[UPLOAD] Resume PDF",
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {'file': {'type': 'string', 'format': 'binary'}, 'query': {'type': 'string'}},
            'required': ['file']
        }
    },
    responses={200: SummarizeOutputSerializer}
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def summarize_article_file_view(request):
    # Validação manual simples para arquivo
    if 'file' not in request.data:
        return Response({"error": "Arquivo não fornecido."}, status=status.HTTP_400_BAD_REQUEST)
    
    file_obj = request.data['file']
    query = request.data.get('user_query')
    
    # Extrai texto do arquivo enviado
    text_result = extract_text_from_file_obj(file_obj)
    if "error" in text_result:
         return Response(text_result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
         
    # Agora chamamos a sumarização com o TEXTO extraído
    from analyzer.services import summarize_article_with_gemini
    result = summarize_article_with_gemini(text_result['text'], natural_language_query=query)
    
    return _handle_summarize_response(result)

@extend_schema(
    summary="[JSON] Extrair Texto de Artigo",
    description="Baixa o PDF (se URL) e retorna apenas o texto puro.",
    request=SummarizeJsonInputSerializer, # Reutiliza o input simples
    responses={200: ExtractTextOutputSerializer}
)
@api_view(['POST'])
def extract_text_json_view(request):
    serializer = SummarizeJsonInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    result = extract_text_content(
        serializer.validated_data['input_value'],
        is_url=serializer.validated_data['is_url']
    )
    if "error" in result:
        return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return Response(result)

@extend_schema(
    summary="[UPLOAD] Extrair Texto de PDF",
    description="Recebe upload de PDF e retorna apenas o texto puro.",
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {'file': {'type': 'string', 'format': 'binary'}},
            'required': ['file']
        }
    },
    responses={200: ExtractTextOutputSerializer}
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def extract_text_file_view(request):
    if 'file' not in request.data:
        return Response({"error": "Arquivo não fornecido."}, status=status.HTTP_400_BAD_REQUEST)
    
    file_obj = request.data['file']
    result = extract_text_from_file_obj(file_obj)
    
    if "error" in result:
        return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return Response(result)


@extend_schema(
    summary="Chat com Contexto do Artigo",
    description="Recebe o texto do artigo (contexto) e o histórico de mensagens, e retorna a resposta da IA.",
    request=ChatInputSerializer,
    responses={200: ChatOutputSerializer}
)
@api_view(['POST'])
def chat_document_view(request):
    serializer = ChatInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    
    context = validated_data['context']
    messages = validated_data['messages']
    
    # CORREÇÃO À PROVA DE FALHAS: Converte cada item para um dicionário Python nativo
    messages_list = [
        {"role": str(m['role']), "content": str(m['content'])} 
        for m in messages
    ]
    
    result = chat_with_context(context, messages_list)
    
    if "error" in result:
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(result)

# --- ROTA DO FORMATADOR ---
@extend_schema(
    summary="Formata Texto",
    responses={200: {'type': 'object', 'properties': {'pdf_url': {'type': 'string'}, 'tex_url': {'type': 'string'}}}}
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def format_text_view(request):
    serializer = FormatTextSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
        
    uploaded_file = request.data['file']
    filename = Path(uploaded_file.name).stem
    style = request.data.get('style')
    extracted_text = extract_text_from_file(uploaded_file)
    
    # Chama o serviço que agora retorna um dicionário
    result = format_text_with_gemini(extracted_text, style, filename)

    if result.get("success"):
        base_name = result["base_filename"]
        # RETORNA JSON COM AS URLS PARA DOWNLOAD
        # Importante: Começa com /download/ para não duplicar o /api no frontend
        return Response({
            "message": "Sucesso",
            "pdf_download_url": f"/download/{base_name}/pdf/",
            "tex_download_url": f"/download/{base_name}/tex/"
        }, status=200)
    else:
        return Response({"error": result.get("error")}, status=500)

# 2. Nova view para Download (GET)
@api_view(['GET'])
def download_file_view(request, filename, file_type):
    """
    Rota para baixar arquivos 'pdf' ou 'tex'.
    """
    base_dir = Path(__file__).resolve().parent.parent
    folder_path = base_dir / 'arquivos'
    
    print(f"DEBUG: Buscando download em: {folder_path}") # Ajuda a ver no terminal

    if file_type == 'pdf':
        file_path = folder_path / f"{filename}.pdf"
        mime_type = 'application/pdf'
    elif file_type == 'tex':
        file_path = folder_path / f"{filename}.tex"
        if not file_path.exists():
             file_path = folder_path / f"{filename}_temp.tex"
        mime_type = 'text/plain'
    else:
        return Response({"error": "Tipo inválido"}, status=400)

    if file_path.exists():
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=mime_type)
            response['Content-Disposition'] = f'attachment; filename={file_path.name}'
            return response
    
    raise Http404("Arquivo não encontrado.")
    
    