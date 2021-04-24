# pages/views.py
import time
from hashlib import sha256

from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView
from django.http import JsonResponse


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        data = {}
        return JsonResponse(data)

