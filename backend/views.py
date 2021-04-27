from django.http import JsonResponse
from backend.nlp_new import parse


def index(request):
    process_description = request.POST.get('process_description', False)

    if process_description:
        results = parse(process_description)
    else:
        results = []

    return JsonResponse(results, safe=False)
