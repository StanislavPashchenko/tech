from catalog.models import Category


class BrandCategoryAdminEntry(Category):
    class Meta:
        proxy = True
        app_label = 'brands'
        verbose_name = 'Тип техники'
        verbose_name_plural = 'Типы техники'
