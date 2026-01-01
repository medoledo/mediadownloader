import yt_dlp
import random
import os
import logging
import requests
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse
from django.core import signing
from .serializers import InstagramDownloadSerializer
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
]

_COOKIE_FILES_CACHE = None
_COOKIE_LAST_UPDATE = 0

def get_cookie_files():
    global _COOKIE_FILES_CACHE, _COOKIE_LAST_UPDATE
    if _COOKIE_FILES_CACHE is None or time.time() - _COOKIE_LAST_UPDATE > 300:
        cookies_dir = settings.BASE_DIR / 'cookies_instagram'
        if os.path.exists(cookies_dir):
            _COOKIE_FILES_CACHE = [str(cookies_dir / f) for f in os.listdir(cookies_dir) if f.endswith('.txt')]
        else:
            _COOKIE_FILES_CACHE = []
        _COOKIE_LAST_UPDATE = time.time()
    return _COOKIE_FILES_CACHE

class InstagramDownloadView(APIView):
    def post(self, request):
        serializer = InstagramDownloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data['url'].split('?')[0]
        cache_key = f"insta_dl_{url}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        cookie_files = get_cookie_files()
        available_cookies = [cf for cf in cookie_files if not cache.get(f"bench_cookie_{os.path.basename(cf)}")]
        
        if not available_cookies and cookie_files:
            return Response({'error': 'All accounts on cool-down.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        attempts = available_cookies if available_cookies else [None]
        random.shuffle(attempts)
        
        for cookie_file in attempts[:3]:
            time.sleep(random.uniform(0.5, 1.5))
            ydl_opts = {
                'format': 'best',
                'force_ipv4': True,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'user_agent': random.choice(USER_AGENTS),
                'cookiefile': cookie_file,
                'extractor_retries': 1,
                'http_headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                }
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_url = info.get('url')
                    title = info.get('title', 'Instagram Video')
                    
                    signer = signing.TimestampSigner()
                    token = signer.sign_object({'url': video_url, 'title': title})
                    proxy_url = f"{request.scheme}://{request.get_host()}/api/instagram/stream/?token={token}"

                    response_data = {
                        'title': title,
                        'download_url': video_url,
                        'proxy_url': proxy_url,
                        'thumbnail': info.get('thumbnail'),
                        'source': 'instagram'
                    }
                    cache.set(cache_key, response_data, timeout=3600)
                    return Response(response_data, status=status.HTTP_200_OK)

            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e).lower()
                if cookie_file and any(x in error_msg for x in ["429", "login", "challenge"]):
                    cache.set(f"bench_cookie_{os.path.basename(cookie_file)}", True, timeout=3600)
                    continue
                break
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'error': 'Service busy or video unavailable.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

class InstagramProxyView(APIView):
    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)
        
        signer = signing.TimestampSigner()
        try:
            data = signer.unsign_object(token, max_age=3600)
            real_url, title = data['url'], data.get('title', 'Instagram_Video')
        except signing.BadSignature:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            external_response = requests.get(real_url, stream=True, timeout=10, proxies={"http": None, "https": None})
            response = StreamingHttpResponse(
                external_response.iter_content(chunk_size=65536),
                content_type=external_response.headers.get('content-type', 'video/mp4')
            )
            filename = f"{title}.mp4".replace('"', '').replace('/', '_')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response({'error': f"Stream failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)