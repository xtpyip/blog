from django.shortcuts import render
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse
import re
from users.models import User
from django.db import DatabaseError
from django.shortcuts import redirect
from django.urls import reverse


# Create your views here.
class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        '''
        1.接收数据
        2。验证数据
        3。保存注册信息
        4。返回响应跳转到指定页面
        :param request:
        :return:
        '''
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        sms_code = request.POST.get('sms_code')
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest('缺少重要的参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号输写错误')
        if not re.match(r'^[0-9A-Za-z]{8,20}', password):
            return HttpResponseBadRequest('请输入8-20位的数字与字母')
        if password != password2:
            return HttpResponseBadRequest("两次密码输入不一致")

        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest("验证码已过期")
        if redis_sms_code.decode() != sms_code:
            return HttpResponseBadRequest("手机验证码输入错误")
        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest("注册失败")

        from django.contrib.auth import login
        login(request, user)

        response = redirect(reverse('home:index'))
        response.set_cookie('is_login', True)
        # return HttpResponse('注册成功，重定向到首页')
        response.set_cookie('username', user.username, max_age=7 * 24 * 60 * 60)
        return response


from libs.captcha.captcha import captcha
from django_redis import get_redis_connection


class ImageCode(View):
    def get(self, request):
        '''
        1。获取从前端来的请求中的uuid
        2. 判断uuid
        3。通过调用captcha 来生成图片验证码（图片二进制，图片内容）
        4。并将uuid与图片内容存在redis中，设置实效
        5。返回图片二进制
        :param request:
        :return:
        '''
        uuid = request.GET.get('uuid')
        if uuid is None:
            return HttpResponseBadRequest('没有传递uuid')

        text, image = captcha.generate_captcha()
        redis_conn = get_redis_connection('default')
        redis_conn.setex('img:%s' % uuid, 300, text)
        return HttpResponse(image, content_type='image/jpeg')
        # pass


from django.http.response import JsonResponse
from utils.response_code import RETCODE
import logging

logger = logging.getLogger('django')
from random import randint
from libs.yuntongxun.sms import CCP


class SmsCodeView(View):
    def get(self, request):
        '''
        1. 接收参数
        2。参数的验证
            参数是否完整
            图片验证码的验证

        3》生成短信验证码
        4》保存短信验证码到redis
        5》发送短信
        6》返回响应结果
        :param request:
        :return:
        '''
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')

        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必要的参数'})
        redis_conn = get_redis_connection('default')
        redis_image_code = redis_conn.get('img:%s' % uuid)
        if redis_image_code is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码已过期'})
        try:
            redis_conn.delete('img:%s' % uuid)
        except Exception as e:
            logger.error(e)
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码错误'})

        sms_code = '%06d' % randint(0, 999999)
        logger.info(sms_code)
        redis_conn.setex('sms:%s' % mobile, 300, sms_code)
        CCP().send_template_sms(mobile, [sms_code, 5], 1)
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '短信发送成功'})


class LoginView(View):
    def get(self, request):

        return render(request, 'login.html')

    def post(self, request):
        '''
        1. 接收参数
        2. 参数的验证
        3. 用户谁认证登陆
        4。 状态的保持
        5。 根据用户选择的是否记住登陆状态来进行判断
        6。 为了首页显示我们需要设置一些cookie
        7。 返回响应
        :param request:
        :return:
        '''
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        if not all([mobile, password]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '必要的参数不全'})
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号填写错误')
        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password):
            return HttpResponseBadRequest("密码输入的格式不正确")
        from django.contrib.auth import authenticate

        user = authenticate(mobile=mobile, password=password)
        if user is None:
            return HttpResponseBadRequest('用户名不存在或者密码错误')
        from django.contrib.auth import login
        login(request, user)
        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse('home:index'))

        if remember != 'on':
            # 浏览器关闭之后
            request.session.set_expiry(0)
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=14 * 24 * 60 * 60)
        else:
            # 默认保存两周
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14 * 24 * 60 * 60)
            response.set_cookie('username', user.username, max_age=14 * 24 * 60 * 60)
        return response


from django.contrib.auth import logout


class LogoutView(View):
    def get(self, request):
        # 1. session 数据的清除
        logout(request)
        # 2. 删除部分cookie数据
        response = redirect(reverse('home:index'))
        response.delete_cookie('is_login')
        # 3. 跳转到首页
        return response


class ForgetPasswordView(View):
    def get(self, request):
        return render(request, 'forget_password.html')

    def post(self, request):
        '''
        1》接收数据
        2》验证数据
        3》根据手机号进行用户信息的查询
        4》如果手机号查询到用户信息则进行用户密码的修改
        5》如果手机号没有查询到用户信息，则进行用户的创建
        6》进行页面跳转
        :param request:
        :return:
        '''
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        sms_code = request.POST.get('sms_code')
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest('缺少重要的参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号书写错误')
        if not re.match(r'^[0-9A-Za-z]{8,20}', password):
            return HttpResponseBadRequest('请输入8-20位的数字与字母')
        if password != password2:
            return HttpResponseBadRequest("两次密码输入不一致")
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest("验证码已过期")
        if redis_sms_code.decode() != sms_code:
            return HttpResponseBadRequest("手机验证码输入错误")

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            try:
                User.objects.create_user(username=mobile, mobile=mobile, password=password)
            except Exception as e:
                logger.error(e)
                return HttpResponseBadRequest("注册失败，请稍候再试")
        else:
            user.set_password(password)
            user.save()
        response = redirect(reverse('users:login'))
        return response


from django.contrib.auth.mixins import LoginRequiredMixin


class UserCenterView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        context = {
            'username': user.username,
            'mobile': user.mobile,
            'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }

        return render(request, 'center.html', context)

    def post(self, request):
        '''
        1。接收参数
        2。将参数保存
        3。更新cookie中的username信息
        4》刷新当前页面（重定向操作）
        5》返回响应
        :param request:
        :return:
        '''
        user = request.user
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)
        avatar = request.FILES.get('avatar')
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改失败，请稍后再试')
        response = redirect(reverse('users:center'))
        response.set_cookie('username', user.username, max_age=14 * 24 * 60 * 60)

        return response


from home.models import ArticleCategory, Article


class WriteBlogView(LoginRequiredMixin, View):
    def get(self, request):
        # 查询所有分类模型
        categories = ArticleCategory.objects.all()
        context = {
            'categories': categories
        }

        return render(request, 'write_blog.html', context=context)

    def post(self, request):
        '''
        1》接收数据
        2》验证数据
        3》数据入库
        4》跳转到指定页面（暂定为首页）
        :param request:
        :return:
        '''
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        tags = request.POST.get('tags')
        summary = request.POST.get('sumary')
        content = request.POST.get('content')
        user = request.user
        if not all([avatar, title, category_id, tags, summary, content]):
            return HttpResponseBadRequest('参数不全')
        try:
            category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('没有此分类')
        try:
            article = Article.objects.create(
                author=user,
                avatar=avatar,
                title=title,
                category=category,
                tags=tags,
                sumary=summary,
                content=content
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest("发布失败，请稍后再试")
        return redirect(reverse('home:index'))
