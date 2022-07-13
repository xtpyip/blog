from django.shortcuts import render
from django.views import View
from home.models import Article, ArticleCategory
from django.http.response import HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse
from home.models import Comment


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
        """
        1.接收文章id信息
        2.根据文章id进行文章数据的查询
        3.查询分类数据
        4.获取分页请求参数
        5.根据文章信息查询评论数据
        6.创建分页器
        7.进行分页处理
        8.组织模板数据
        :param request:
        :return:
        """
        id = request.GET.get('id')
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return render(request, '404.html')
        else:
            article.total_views += 1
            article.save()

        categories = ArticleCategory.objects.all()
        hot_articles = Article.objects.order_by('-total_views')[:9]

        page_size = request.GET.get('page_size', 10)
        page_num = request.GET.get('page_num', 1)

        comments = Comment.objects.filter(article=article).order_by('-created')
        total_count = comments.count()
        from django.core.paginator import Paginator, EmptyPage
        paginator = Paginator(comments, page_size)
        try:
            page_comment = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')
        total_page = paginator.num_pages
        context = {
            'categories': categories,
            'category': article.category,
            'article': article,
            'hot_articles': hot_articles,
            'total_count': total_count,
            'comments': page_comment,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num

        }

        return render(request, 'detail.html', context=context)

    def post(self, request):
        """
        1.先接收用户信息
        2.判断用户是否登录
        3.登录用户则可以接收 form数据
            3.1接收评论数据
            3.2验证文章是否存在
            3.3保存评论数据
            3.4修改文章的评论数量
        4.未登录用户则跳转到登录页面
        :param request:
        :return:
        """
        user = request.user
        if user and user.is_authenticated:
            id = request.POST.get('id')
            content = request.POST.get('content')
            try:
                article = Article.objects.get(id=id)
                pass
            except Article.DoesNotExist:
                return HttpResponseNotFound("没有此文章")
            Comment.objects.create(
                content=content,
                article=article,
                user=user
            )
            article.comments_count += 1
            article.save()
            path = reverse('home:detail') + '?id={}'.format(article.id)
            return redirect(path)
        else:
            return redirect(reverse('users:login'))
