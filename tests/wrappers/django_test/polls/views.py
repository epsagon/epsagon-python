from django.shortcuts import render
from django.http import HttpResponse


def indexA(request):
    return HttpResponse("This is A")

def indexB(request):
    return HttpResponse("This is B")
