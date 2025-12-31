from django.urls import path
from .views import InstagramDownloadView

urlpatterns = [
    path('download/', InstagramDownloadView.as_view(), name='instagram-download'),
]
