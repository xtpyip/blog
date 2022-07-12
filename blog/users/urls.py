from django.urls import path
from users.views import RegisterView,ImageCode,SmsCodeView
urlpatterns = [
    path('register',RegisterView.as_view(),name='register'),
    # 图片验证码的路由
    path('imagecode/',ImageCode.as_view(),name='imageCode'),
    # 手机验证码
    path('smscode/',SmsCodeView.as_view(),name='smsCode')
]