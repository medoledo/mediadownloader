from django.urls import path
from .views import InstagramDownloadView, InstagramProxyView

urlpatterns = [
    path('download/', InstagramDownloadView.as_view(), name='instagram-download'),
    path('stream/', InstagramProxyView.as_view(), name='instagram-stream'),
]
