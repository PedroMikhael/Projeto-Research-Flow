from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    get_status, 
    search_articles_view, 
    summarize_article_json_view, 
    summarize_article_file_view, 
    extract_text_json_view,
    extract_text_file_view, 
    chat_document_view,
    format_text_view, 
    download_file_view,
    RegisterUserView,
    LogoutView,
    FavoriteListCreateView,
    FavoriteDeleteView
)

urlpatterns = [
    path('status/', get_status, name='get_status'),
    path('search/', search_articles_view, name='search_articles'),
    path('summarize/json/', summarize_article_json_view, name='summarize_json'),
    path('summarize/file/', summarize_article_file_view, name='summarize_file'),
    path('extract/json/', extract_text_json_view, name='extract_text_json'),
    path('extract/file/', extract_text_file_view, name='extract_text_file'),
    path('chat/', chat_document_view, name='chat_document'),
    path('format/', format_text_view, name='format_text'),
    path('download/<str:filename>/<str:file_type>/', download_file_view, name='download_file'),
    
    # Auth
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', obtain_auth_token, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Favorites
    path('favorites/', FavoriteListCreateView.as_view(), name='favorites_list_create'),
    path('favorites/<int:pk>/', FavoriteDeleteView.as_view(), name='favorites_delete'),
]