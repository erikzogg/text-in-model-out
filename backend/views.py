from django.http import HttpResponse
from backend.nlp_simple import parse
import json


def index(request):
    results = parse(request.POST['text'])

    return HttpResponse(json.dumps(results))
