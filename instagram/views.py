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
