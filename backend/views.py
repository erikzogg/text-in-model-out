from django.http import HttpResponse
from backend.nlp import parse
import json


def index(request):
    results = parse(request.POST['text'])

    return HttpResponse("<pre>" + json.dumps(results, indent=4) + "</pre>")
