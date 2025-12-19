from django.http import HttpResponse

def index(request):
    return HttpResponse("Data Observability Platform — OK")
