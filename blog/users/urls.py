from django.urls import path
from users.views import RegisterView, ImageCode, SmsCodeView, LoginView, LogoutView,\
    ForgetPasswordView,UserCenterView,WriteBlogView

urlpatterns = [
    path('register', RegisterView.as_view(), name='register'),
    # 图片验证码的路由
    path('imagecode/', ImageCode.as_view(), name='imageCode'),
    # 手机验证码
    path('smscode/', SmsCodeView.as_view(), name='smsCode'),
    # 登陆路由
    path('login/', LoginView.as_view(), name='login'),
    # 退出登陆
    path('logout/', LogoutView.as_view(), name='logout'),
    # 忘记密码
    path('forgetpassword/',ForgetPasswordView.as_view(),name='forgetPassword'),
    # 个人中心
    path('center/',UserCenterView.as_view(),name='center'),
    # 写博客的路由
    path('writeblog/',WriteBlogView.as_view(),name='writeBlog')
]
