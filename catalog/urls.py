from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:lang>/', views.index, name='index_lang'),
    path('<str:lang>/search/', views.search_view, name='search'),
    path('<str:lang>/articles/', views.articles_index, name='articles_index'),
    path('<str:lang>/articles/<int:article_id>/<str:article_slug>/', views.article_detail_view, name='article_detail'),
    path('<str:lang>/products/', views.products_index, name='products_index'),
    path('<str:lang>/products/<str:section_id>/<str:product_slug>/', views.product_detail_view, name='product_detail'),
    path('<str:lang>/products/<str:section_id>/', views.section_view, name='product_section'),
    path('<str:lang>/section/<str:section_id>/', views.section_view, name='section'),
]
