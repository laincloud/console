# -*- coding: utf-8

from django.http import JsonResponse, HttpResponse

# from commons.settings import ARCHON_HOST


class CORSMiddleware:
    def process_request(self, request):
        if request.method == 'OPTIONS':
            r = HttpResponse('', content_type='text/plain', status=200)
            r['Access-Control-Allow-Methods'] = ', '.join(['DELETE', 'GET', 'PATCH', 'POST', 'PUT'])
            r['Access-Control-Allow-Headers'] = ', '.join(['access-token', 'content-type'])
            r['Access-Control-Max-Age'] = 86400
            return r

        return None

    def process_response(self, request, response):
            response['Access-Control-Allow-Origin'] = '*'
            return response
