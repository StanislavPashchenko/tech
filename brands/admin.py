from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from catalog.models import VacuumBrand

from .models import BrandCategoryAdminEntry


class VacuumBrandInline(admin.TabularInline):
    model = VacuumBrand
    extra = 0
    fields = ('name', 'slug', 'product_count')
    readonly_fields = ('product_count',)
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Товаров'


@admin.register(BrandCategoryAdminEntry)
class BrandCategoryAdminEntryAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'brand_count', 'product_count', 'brands_link')
    search_fields = ('name_ru', 'name_ua', 'name_en', 'id_name')
    inlines = (VacuumBrandInline,)
    inline_limit = 120

    def get_inline_instances(self, request, obj=None):
        if obj is not None and obj.brands.count() > self.inline_limit:
            return []
        return super().get_inline_instances(request, obj)

    def brand_count(self, obj):
        return obj.brands.count()
    brand_count.short_description = 'Брэндов'

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Товаров'

    def brands_link(self, obj):
        url = f'{reverse("admin:catalog_vacuumbrand_changelist")}?category__id__exact={obj.id}'
        return format_html('<a href="{}">Открыть бренды</a>', url)
    brands_link.short_description = 'Бренды'


@admin.register(VacuumBrand)
class VacuumBrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'product_count')
    list_filter = ('category',)
    search_fields = ('name', 'slug', 'category__name_ru')

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Товаров'
