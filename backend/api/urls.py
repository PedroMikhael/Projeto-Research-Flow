from django.urls import path
from django.contrib import admin
from django.urls import include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Garanta que a nova view "search_articles_view" foi importada
from .views import get_status, search_articles_view, analyze_article_view 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),

    # Rotas da Documentação (Swagger)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Interface do Swagger UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Interface do ReDoc (outra opção de visualização):
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]