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
        if not re.match(r'^1[3-9]\d{9}$',mobile):
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
        return redirect(reverse('home:index'))
        # return HttpResponse('注册成功，重定向到首页')


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
