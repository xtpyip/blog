from django.shortcuts import render
from django.views import View
from home.models import Article, ArticleCategory
from django.http.response import HttpResponseNotFound


# Create your views here.
class IndexView(View):
    def get(self, request):
        '''
        1》获取所有分类信息
        2》接收用户点击的分类id
        3》根据分类id进行分类的查询
        4》获取分页参数
        5》根据分类信息查询文章数据
        6》创建分页器
        7》进行分页处理
        8》组织数据传递给模板
        :param request:
        :return:
        '''
        categories = ArticleCategory.objects.all()
        category_id = request.GET.get('cat_id', 1)
        try:
            category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseNotFound('没有此分类')

        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 10)
        articles = Article.objects.filter(category=category)
        from django.core.paginator import Paginator, EmptyPage
        paginator = Paginator(articles, per_page=page_size)

        try:
            page_article = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')
        total_page = paginator.num_pages

        context = {
            'categories': categories,
            'category': category,
            'articles': page_article,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num
        }
        return render(request, 'index.html', context=context)


class DetailView(View):
    def get(self, request):
        id = request.GET.get('id')
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            pass
        categories = ArticleCategory.objects.all()
        context = {
            'categories': categories,
            'category': article.category,
            'article': article
        }

        return render(request, 'detail.html', context=context)
