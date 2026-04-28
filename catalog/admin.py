import json

from django import forms
from django.contrib import admin
from django.db import models as django_models
from django.http import JsonResponse
from django.urls import path, reverse
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Article, ArticleImage, Breakdown, BreakdownGroup, Category, Product, VacuumBrand


def _resolve_category_id(form):
    category_id = (
        form.data.get('category') or
        (form.instance.category_id if form.instance and form.instance.pk else None) or
        form.initial.get('category') or
        (form.instance.category_id if form.instance else None)
    )

    if not category_id and hasattr(form, 'request') and form.request.GET.get('category'):
        category_id = form.request.GET.get('category')

    return category_id


def _configure_brand_field(form, brand_options_url):
    category_id = _resolve_category_id(form)

    if category_id:
        try:
            form.fields['brand'].queryset = VacuumBrand.objects.filter(category_id=category_id).order_by('name')
        except (ValueError, TypeError):
            form.fields['brand'].queryset = VacuumBrand.objects.none()
    else:
        form.fields['brand'].queryset = VacuumBrand.objects.none()

    brand_widget = form.fields['brand'].widget
    brand_widget.attrs['data-brand-options-url'] = brand_options_url
    if hasattr(brand_widget, 'widget'):
        brand_widget.widget.attrs['data-brand-options-url'] = brand_options_url


def _configure_breakdown_group_field(form, breakdown_group_options_url):
    if 'breakdown_group' not in form.fields and 'breakdown_groups' not in form.fields:
        return

    category_id = _resolve_category_id(form)
    queryset = BreakdownGroup.objects.none()

    if category_id:
        try:
            queryset = BreakdownGroup.objects.filter(category_id=category_id)
            queryset = queryset.order_by('name')
        except (ValueError, TypeError):
            queryset = BreakdownGroup.objects.none()

    if 'breakdown_group' in form.fields:
        form.fields['breakdown_group'].queryset = queryset
        breakdown_group_widget = form.fields['breakdown_group'].widget
        breakdown_group_widget.attrs['data-breakdown-group-options-url'] = breakdown_group_options_url
        if hasattr(breakdown_group_widget, 'widget'):
            breakdown_group_widget.widget.attrs['data-breakdown-group-options-url'] = breakdown_group_options_url

    if 'breakdown_groups' in form.fields:
        form.fields['breakdown_groups'].queryset = queryset
        additional_breakdown_group_widget = form.fields['breakdown_groups'].widget
        additional_breakdown_group_widget.attrs['data-breakdown-group-options-url'] = breakdown_group_options_url
        if hasattr(additional_breakdown_group_widget, 'widget'):
            additional_breakdown_group_widget.widget.attrs['data-breakdown-group-options-url'] = breakdown_group_options_url


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'specs_ru': forms.Textarea(attrs={'rows': 15, 'style': 'font-family: monospace;'}),
            'specs_ua': forms.Textarea(attrs={'rows': 15, 'style': 'font-family: monospace;'}),
            'specs_en': forms.Textarea(attrs={'rows': 15, 'style': 'font-family: monospace;'}),
            'images': forms.Textarea(attrs={'rows': 5, 'style': 'font-family: monospace;'}),
        }

    class Media:
        js = ('catalog/admin/product_brand_filter.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'breakdown_groups' in self.fields:
            self.fields['breakdown_groups'].widget = forms.SelectMultiple(attrs={'size': 1})
            self.fields['breakdown_groups'].help_text = ''
        for field in ['specs_ru', 'specs_ua', 'specs_en', 'images']:
            if self.instance and getattr(self.instance, field):
                val = getattr(self.instance, field)
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except:
                        pass
                try:
                    formatted_json = json.dumps(val, indent=4, ensure_ascii=False)
                    self.initial[field] = formatted_json
                except (ValueError, TypeError):
                    pass

        _configure_brand_field(self, reverse('admin:catalog_product_brand_options'))
        _configure_breakdown_group_field(self, reverse('admin:catalog_product_breakdown_group_options'))

    def clean_specs_ru(self):
        return self._clean_json_field('specs_ru')

    def clean_specs_ua(self):
        return self._clean_json_field('specs_ua')

    def clean_specs_en(self):
        return self._clean_json_field('specs_en')

    def clean_images(self):
        return self._clean_json_field('images')

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        brand = cleaned_data.get('brand')
        breakdown_group = cleaned_data.get('breakdown_group')
        breakdown_groups = cleaned_data.get('breakdown_groups')

        if breakdown_group:
            if category and breakdown_group.category_id != category.id:
                self.add_error('breakdown_group', 'Группа поломок должна относиться к выбранному типу техники.')

        if breakdown_groups is not None and category:
            for group in breakdown_groups:
                if group.category_id != category.id:
                    self.add_error('breakdown_groups', 'Дополнительные группы поломок должны относиться к выбранному типу техники.')
                    break

        if breakdown_group and breakdown_groups is not None:
            cleaned_data['breakdown_groups'] = breakdown_groups.exclude(id=breakdown_group.id)

        return cleaned_data

    def _clean_json_field(self, field):
        data = self.cleaned_data[field]
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Неверный формат JSON")
        return data


class BreakdownGroupAdminForm(forms.ModelForm):
    class Meta:
        model = BreakdownGroup
        fields = '__all__'

    class Media:
        js = ('catalog/admin/product_brand_filter.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_brand_field(self, reverse('admin:catalog_breakdown_group_brand_options'))
        if 'name' in self.fields:
            self.fields['name'].required = False

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        brand = cleaned_data.get('brand')

        if not brand:
            self.add_error('brand', 'Выберите бренд для группы поломок.')
            return cleaned_data

        if category and brand.category_id != category.id:
            self.add_error('brand', 'Бренд должен относиться к выбранному типу техники.')

        if not cleaned_data.get('name') and category and brand:
            cleaned_data['name'] = f'{category.name_ru} {brand.name}'.strip()

        return cleaned_data


class BreakdownInline(admin.StackedInline):
    model = Breakdown
    extra = 1
    formfield_overrides = {
        django_models.TextField: {'widget': forms.Textarea(attrs={'rows': 8})},
    }
    fields = (
        ('title', 'title_ua', 'title_en'),
        ('possible_causes', 'possible_causes_ua', 'possible_causes_en'),
        ('what_to_check', 'what_to_check_ua', 'what_to_check_en'),
        ('how_to_fix', 'how_to_fix_ua', 'how_to_fix_en'),
    )


class ArticleImageInline(admin.StackedInline):
    model = ArticleImage
    extra = 1
    fields = (
        'image',
        ('alt_ru', 'alt_ua', 'alt_en'),
        'sort_order',
        'image_preview',
    )
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.pk and obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="180" style="object-fit: cover; border: 1px solid #ccc;" />')
        return '-'

    image_preview.short_description = 'Превью'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'id_name', 'folder', 'product_count')
    search_fields = ('name_ru', 'name_ua', 'name_en', 'id_name')

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Товаров'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name_ru', 'brand', 'category', 'breakdown_group', 'image_preview')
    list_filter = ('category', 'brand', 'breakdown_group')
    search_fields = ('name_ru', 'name_ua', 'name_en', 'description_ru', 'breakdown_group__name')
    readonly_fields = ('image_preview', 'images_list')
    
    class Media:
        js = ('catalog/admin/product_brand_filter.js',)

    fieldsets = (
        ('Общая информация', {
            'fields': ('category', 'brand', 'breakdown_group', 'breakdown_groups', 'product_folder', 'source_url')
        }),
        ('Русский язык (RU)', {
            'fields': ('name_ru', 'description_ru', 'specs_ru'),
        }),
        ('Українська мова (UA)', {
            'fields': ('name_ua', 'description_ua', 'specs_ua'),
        }),
        ('English (EN)', {
            'fields': ('name_en', 'description_en', 'specs_en'),
        }),
        ('Изображения', {
            'fields': ('images', 'images_list'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        form_class.request = request
        return form_class

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'brand-options/',
                self.admin_site.admin_view(self.brand_options_view),
                name='catalog_product_brand_options',
            ),
            path(
                'breakdown-group-options/',
                self.admin_site.admin_view(self.breakdown_group_options_view),
                name='catalog_product_breakdown_group_options',
            ),
        ]
        return custom_urls + urls

    def brand_options_view(self, request):
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse({'results': []})

        results = list(
            VacuumBrand.objects.filter(category_id=category_id)
            .order_by('name')
            .values('id', 'name')
        )
        return JsonResponse({'results': results})

    def breakdown_group_options_view(self, request):
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse({'results': []})

        results = list(
            BreakdownGroup.objects.filter(category_id=category_id)
            .order_by('name')
            .values('id', 'name')
        )
        return JsonResponse({'results': results})

    def image_preview(self, obj):
        if obj.images and len(obj.images) > 0:
            return mark_safe(f'<img src="{obj.images[0]}" width="50" height="50" style="object-fit: contain;" />')
        return "-"
    image_preview.short_description = 'Превью'

    def images_list(self, obj):
        html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
        for img in obj.images:
            html += f'<div style="text-align: center;"><img src="{img}" width="150" style="border: 1px solid #ccc;" /><br/><span style="font-size: 10px;">{img}</span></div>'
        html += '</div>'
        return mark_safe(html)
    images_list.short_description = 'Все изображения'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title_ru', 'is_published', 'published_at', 'created_at')
    list_filter = ('is_published', 'published_at', 'created_at')
    search_fields = (
        'title_ru',
        'title_ua',
        'title_en',
        'excerpt_ru',
        'excerpt_ua',
        'excerpt_en',
        'content_ru',
        'content_ua',
        'content_en',
        'slug',
    )
    prepopulated_fields = {'slug': ('title_ru',)}
    inlines = (ArticleImageInline,)

    fieldsets = (
        ('Общая информация', {
            'fields': ('slug', 'is_published', 'published_at')
        }),
        ('Русский язык (RU)', {
            'fields': ('title_ru', 'excerpt_ru', 'content_ru'),
        }),
        ('Українська мова (UA)', {
            'fields': ('title_ua', 'excerpt_ua', 'content_ua'),
        }),
        ('English (EN)', {
            'fields': ('title_en', 'excerpt_en', 'content_en'),
        }),
    )


@admin.register(BreakdownGroup)
class BreakdownGroupAdmin(admin.ModelAdmin):
    form = BreakdownGroupAdminForm
    change_list_template = 'admin/catalog/breakdowngroup/change_list.html'
    list_display = ('category_path_link', 'brand_path_link', 'name', 'breakdowns_count', 'products_count')
    list_display_links = ('name',)
    list_filter = ('category', 'brand')
    search_fields = (
        'name',
        'brand__name',
        'category__name_ru',
        'breakdowns__title',
        'breakdowns__title_ua',
        'breakdowns__title_en',
    )
    inlines = (BreakdownInline,)

    class Media:
        js = ('catalog/admin/product_brand_filter.js',)

    fieldsets = (
        ('Общая информация', {'fields': ('category', 'brand', 'name')}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        form_class.request = request
        return form_class

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'brand-options/',
                self.admin_site.admin_view(self.brand_options_view),
                name='catalog_breakdown_group_brand_options',
            ),
            path(
                'path/<int:category_id>/',
                self.admin_site.admin_view(self.by_category_redirect_view),
                name='catalog_breakdown_group_by_category',
            ),
            path(
                'path/<int:category_id>/<int:brand_id>/',
                self.admin_site.admin_view(self.by_category_brand_redirect_view),
                name='catalog_breakdown_group_by_category_brand',
            ),
        ]
        return custom_urls + urls

    def brand_options_view(self, request):
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse({'results': []})

        results = list(
            VacuumBrand.objects.filter(category_id=category_id)
            .order_by('name')
            .values('id', 'name')
        )
        return JsonResponse({'results': results})

    def breakdowns_count(self, obj):
        return obj.breakdowns.count()

    breakdowns_count.short_description = 'Поломок'

    def products_count(self, obj):
        return obj.products.count()

    products_count.short_description = 'Товаров'

    def category_path_link(self, obj):
        url = reverse('admin:catalog_breakdown_group_by_category', args=[obj.category_id])
        return format_html('<a href="{}">{}</a>', url, obj.category.name_ru)

    category_path_link.short_description = 'Тип техники'
    category_path_link.admin_order_field = 'category__name_ru'

    def brand_path_link(self, obj):
        if not obj.brand_id:
            return '-'
        url = reverse('admin:catalog_breakdown_group_by_category_brand', args=[obj.category_id, obj.brand_id])
        return format_html('<a href="{}">{}</a>', url, obj.brand.name)

    brand_path_link.short_description = 'Бренд'
    brand_path_link.admin_order_field = 'brand__name'

    def by_category_redirect_view(self, request, category_id):
        changelist_url = reverse('admin:catalog_breakdowngroup_changelist')
        return redirect(f'{changelist_url}?category__id__exact={category_id}')

    def by_category_brand_redirect_view(self, request, category_id, brand_id):
        changelist_url = reverse('admin:catalog_breakdowngroup_changelist')
        return redirect(f'{changelist_url}?category__id__exact={category_id}&brand__id__exact={brand_id}')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        base_url = reverse('admin:catalog_breakdowngroup_changelist')
        extra_context['category_shortcuts'] = [
            {
                'id': category.id,
                'name': category.name_ru,
                'url': f'{base_url}?category__id__exact={category.id}',
            }
            for category in Category.objects.order_by('name_ru')
        ]
        try:
            return super().changelist_view(request, extra_context=extra_context)
        except TemplateDoesNotExist:
            original_template = self.change_list_template
            self.change_list_template = None
            try:
                return super().changelist_view(request, extra_context=extra_context)
            finally:
                self.change_list_template = original_template
