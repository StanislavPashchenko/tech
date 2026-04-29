import os

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.text import slugify


ARTICLE_IMAGE_CLOUDFLARE_PREFIX = 'https://pub-6917b9abd5364cef8cbe869ff198c43a.r2.dev/items/test/'

class Category(models.Model):
    id_name = models.CharField(max_length=100, unique=True)
    name_ru = models.CharField(max_length=255)
    name_ua = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    folder = models.CharField(max_length=255)

    def __str__(self):
        return self.name_ru


class VacuumBrand(models.Model):
    category = models.ForeignKey(Category, related_name='brands', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)

    class Meta:
        ordering = ['name']
        verbose_name = 'Брэнд'
        verbose_name_plural = 'Брэнды'
        constraints = [
            models.UniqueConstraint(fields=['category', 'name'], name='catalog_vacuumbrand_category_name_uniq'),
            models.UniqueConstraint(fields=['category', 'slug'], name='catalog_vacuumbrand_category_slug_uniq'),
        ]

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    brand = models.ForeignKey(VacuumBrand, related_name='products', on_delete=models.SET_NULL, blank=True, null=True)
    breakdown_group = models.ForeignKey(
        'BreakdownGroup',
        related_name='products',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Группа поломок',
    )
    breakdown_groups = models.ManyToManyField(
        'BreakdownGroup',
        related_name='products_multi',
        blank=True,
        verbose_name='Дополнительные группы поломок',
    )
    
    # Russian
    name_ru = models.CharField(max_length=255, blank=True, null=True)
    description_ru = models.TextField(blank=True, null=True)
    specs_ru = models.JSONField(default=dict)
    
    # Ukrainian
    name_ua = models.CharField(max_length=255, blank=True, null=True)
    description_ua = models.TextField(blank=True, null=True)
    specs_ua = models.JSONField(default=dict)
    
    # English
    name_en = models.CharField(max_length=255, blank=True, null=True)
    description_en = models.TextField(blank=True, null=True)
    specs_en = models.JSONField(default=dict)
    
    # Global fields
    images = models.JSONField(default=list)
    source_url = models.URLField(max_length=500, blank=True, null=True)
    product_folder = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name_ru or self.name_en or "Unnamed Product"


class BreakdownGroup(models.Model):
    category = models.ForeignKey(Category, related_name='breakdown_groups', on_delete=models.CASCADE, verbose_name='Тип техники')
    brand = models.ForeignKey(
        VacuumBrand,
        related_name='breakdown_groups',
        on_delete=models.SET_NULL,
        verbose_name='Бренд',
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255, verbose_name='Группа поломок', blank=True)

    class Meta:
        ordering = ['category__name_ru', 'brand__name', 'name']
        verbose_name = 'Группа поломок'
        verbose_name_plural = 'Группы поломок'
        constraints = [
            models.UniqueConstraint(fields=['category', 'brand', 'name'], name='catalog_breakdowngroup_category_brand_name_uniq'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.name and self.category_id and self.brand_id:
            self.name = f'{self.category.name_ru} {self.brand.name}'.strip()
        super().save(*args, **kwargs)


class Breakdown(models.Model):
    breakdown_group = models.ForeignKey(BreakdownGroup, related_name='breakdowns', on_delete=models.CASCADE, verbose_name='Группа поломок')
    title = models.CharField(max_length=255, verbose_name='Поломка (RU)', blank=True, default='')
    description = models.TextField(verbose_name='Описание (RU)', blank=True, default='')
    possible_causes = models.TextField(verbose_name='Возможные причины (RU)', blank=True, default='')
    what_to_check = models.TextField(verbose_name='Что проверить (RU)', blank=True, default='')
    how_to_fix = models.TextField(verbose_name='Как исправить (RU)', blank=True, default='')
    title_ua = models.CharField(max_length=255, verbose_name='Поломка (UA)', blank=True, default='')
    description_ua = models.TextField(verbose_name='Описание (UA)', blank=True, default='')
    possible_causes_ua = models.TextField(verbose_name='Возможные причины (UA)', blank=True, default='')
    what_to_check_ua = models.TextField(verbose_name='Что проверить (UA)', blank=True, default='')
    how_to_fix_ua = models.TextField(verbose_name='Как исправить (UA)', blank=True, default='')
    title_en = models.CharField(max_length=255, verbose_name='Поломка (EN)', blank=True, default='')
    description_en = models.TextField(verbose_name='Описание (EN)', blank=True, default='')
    possible_causes_en = models.TextField(verbose_name='Возможные причины (EN)', blank=True, default='')
    what_to_check_en = models.TextField(verbose_name='Что проверить (EN)', blank=True, default='')
    how_to_fix_en = models.TextField(verbose_name='Как исправить (EN)', blank=True, default='')

    class Meta:
        ordering = ['breakdown_group__name', 'title']
        verbose_name = 'Поломка'
        verbose_name_plural = 'Поломки'

    def __str__(self):
        return f'{self.title} — {self.breakdown_group.name}'


class Article(models.Model):
    slug = models.SlugField(max_length=255, unique=True, verbose_name='Slug')
    is_published = models.BooleanField(default=True, verbose_name='Опубликовано')
    published_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата публикации')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    title_ru = models.CharField(max_length=255, verbose_name='Заголовок (RU)')
    excerpt_ru = models.TextField(blank=True, default='', verbose_name='Краткое описание (RU)')
    content_ru = models.TextField(verbose_name='Текст статьи (RU)')

    title_ua = models.CharField(max_length=255, verbose_name='Заголовок (UA)')
    excerpt_ua = models.TextField(blank=True, default='', verbose_name='Краткое описание (UA)')
    content_ua = models.TextField(verbose_name='Текст статьи (UA)')

    title_en = models.CharField(max_length=255, verbose_name='Заголовок (EN)')
    excerpt_en = models.TextField(blank=True, default='', verbose_name='Краткое описание (EN)')
    content_en = models.TextField(verbose_name='Текст статьи (EN)')

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'

    def __str__(self):
        return self.title_ru or self.title_ua or self.title_en or self.slug

    def save(self, *args, **kwargs):
        if not self.slug:
            base_title = self.title_ru or self.title_ua or self.title_en or 'article'
            self.slug = slugify(base_title, allow_unicode=True)[:255] or 'article'
        super().save(*args, **kwargs)


class ArticleImage(models.Model):
    article = models.ForeignKey(Article, related_name='images', on_delete=models.CASCADE, verbose_name='Статья')
    cloudflare_url = models.URLField(
        max_length=1000,
        blank=True,
        default='',
        verbose_name='Ссылка Cloudflare (R2)',
        help_text='Пример: https://pub-...r2.dev/items/test/1.jpg',
    )
    image = models.FileField(
        upload_to='articles/%Y/%m/',
        verbose_name='Изображение (legacy)',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif'])],
        blank=True,
        null=True,
    )
    alt_ru = models.CharField(max_length=255, blank=True, default='', verbose_name='Alt (RU)')
    alt_ua = models.CharField(max_length=255, blank=True, default='', verbose_name='Alt (UA)')
    alt_en = models.CharField(max_length=255, blank=True, default='', verbose_name='Alt (EN)')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Изображение статьи'
        verbose_name_plural = 'Изображения статей'

    @property
    def image_url(self):
        if self.cloudflare_url:
            return self.cloudflare_url
        if self.image:
            return self.image.url
        return ''

    def _build_cloudflare_url_from_legacy_image(self):
        if not self.image:
            return ''
        filename = os.path.basename(self.image.name or '').strip()
        if not filename:
            return ''
        return f'{ARTICLE_IMAGE_CLOUDFLARE_PREFIX}{filename}'

    def save(self, *args, **kwargs):
        if not self.cloudflare_url:
            legacy_url = self._build_cloudflare_url_from_legacy_image()
            if legacy_url:
                self.cloudflare_url = legacy_url
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Image #{self.pk or "new"} for {self.article}'
