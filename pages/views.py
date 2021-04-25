# pages/views.py
from django.views.generic import TemplateView

import core.engine as engine


SEARCH_ENGINE = engine.SearchEngine()


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = int(self.request.GET.get('page', '1'))
        page = page if page > 0 else 1
        request_text = self.request.GET.get('request', '')
        request_text = request_text.strip()

        states_per_page = 10
        width_paginator = 5

        context['page'] = page
        context['width_paginator'] = width_paginator
        context['number_pages'] = 0
        context['page_path'] = f'/?request={request_text}'
        context['request'] = request_text
        context['snippets'] = []
        context['is_request'] = False
        context['is_error_in_request_syntax'] = not engine.SearchEngine.check_request(request_text)
        context['total_states'] = 0
        context['request_time'] = 0

        if request_text and engine.SearchEngine.check_request(request_text):
            context['is_request'] = True
            serp, request_time, number_pages, total_states = SEARCH_ENGINE.SERP(request_text, page, states_per_page)
            context['number_pages'] = number_pages
            context['total_states'] = total_states
            context['request_time'] = request_time
            for title, link, text in serp:
                context['snippets'].append({'title': title, 'link': link, 'text': text})

        context['window_pages'] = list(range(max(2, page - width_paginator),
                                             min(page + width_paginator, context['number_pages']-1)+1))

        return context


