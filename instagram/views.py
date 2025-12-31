import yt_dlp
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import InstagramDownloadSerializer

class InstagramDownloadView(APIView):
    def post(self, request):
        serializer = InstagramDownloadSerializer(data=request.data)
        if serializer.is_valid():
            url = serializer.validated_data['url']
            
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'extractor_retries': 3,
                'sleep_interval': 2,
                'max_sleep_interval': 5,
                'http_headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_url = info.get('url')
                    title = info.get('title', 'Instagram Video')
                    thumbnail = info.get('thumbnail')
                    
                    return Response({
                        'title': title,
                        'download_url': video_url,
                        'thumbnail': thumbnail,
                        'source': 'instagram'
                    }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
