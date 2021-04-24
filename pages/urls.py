from django.urls import path, re_path
from .views import HomePageView
from django.views.generic import RedirectView

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/favicon.ico'), name='favicon'),
]
