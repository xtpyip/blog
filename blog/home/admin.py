from django.contrib import admin
from home.models import ArticleCategory,Article,Comment
# Register your models here.
# 注册模型
admin.site.register(ArticleCategory)
admin.site.register(Article)
admin.site.register(Comment)