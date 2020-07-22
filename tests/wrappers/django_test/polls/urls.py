from django.urls import path

from . import views

urlpatterns = [
    path('a', views.indexA, name='a'),
    path('b', views.indexB, name='b'),
]