from django.urls import path
from .views import get_status, search_articles_view, summarize_article_json_view, summarize_article_file_view, extract_text_json_view,extract_text_file_view, chat_document_view,format_text_view

urlpatterns = [
    path('status/', get_status, name='get_status'),
    path('search/', search_articles_view, name='search_articles'),
    path('summarize/json/', summarize_article_json_view, name='summarize_json'),
    path('summarize/file/', summarize_article_file_view, name='summarize_file'),
    path('extract/json/', extract_text_json_view, name='extract_text_json'),
    path('extract/file/', extract_text_file_view, name='extract_text_file'),
    path('chat/', chat_document_view, name='chat_document'),
    path('format/', format_text_view, name='format_text'),
]