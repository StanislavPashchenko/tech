from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    re_path(r'^(?P<lang>ru|ua|en)/$', views.index, name='index_lang'),
    re_path(r'^(?P<lang>ru|ua|en)/search/$', views.search_view, name='search'),
    re_path(r'^(?P<lang>ru|ua|en)/articles/$', views.articles_index, name='articles_index'),
    re_path(r'^(?P<lang>ru|ua|en)/articles/(?P<article_id>\d+)/(?P<article_slug>[^/]+)/$', views.article_detail_view, name='article_detail'),
    re_path(r'^(?P<lang>ru|ua|en)/products/$', views.products_index, name='products_index'),
    re_path(r'^(?P<lang>ru|ua|en)/products/(?P<section_id>[^/]+)/(?P<product_slug>[^/]+)/(?P<breakdown_slug>[^/]+)/$', views.breakdown_detail_view, name='breakdown_detail'),
    re_path(r'^(?P<lang>ru|ua|en)/products/(?P<section_id>[^/]+)/(?P<product_slug>[^/]+)/$', views.product_detail_view, name='product_detail'),
    re_path(r'^(?P<lang>ru|ua|en)/products/(?P<section_id>[^/]+)/$', views.section_view, name='product_section'),
    re_path(r'^(?P<lang>ru|ua|en)/section/(?P<section_id>[^/]+)/$', views.section_view, name='section'),
]
