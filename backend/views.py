from django.http import HttpResponse
from backend.nlp import parse


def index(request):
    results = parse(request.POST['text'])

    return HttpResponse(str(results))
