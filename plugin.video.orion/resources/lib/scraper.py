# -*- coding: utf-8 -*-
"""
Torrent & Stream Scraper for Orion v2.2.0
Scrapes multiple sources including Torrentio, MediaFusion, Orionoid, torrents, and direct streaming sites
"""

import urllib.request
import urllib.parse
import re
import ssl
import json
import xbmc
import xbmcaddon

SSL_CONTEXT = ssl._create_unverified_context()
ADDON = xbmcaddon.Addon()

# Stremio Addon Base URLs
TORRENTIO_BASE = "https://torrentio.strem.fun"
MEDIAFUSION_BASE = "https://mediafusion.elfhosted.com"

# VidSrc domains (active as of 2025-2026)
VIDSRC_DOMAINS = [
    "https://vidsrc.to",
    "https://vidsrc.pro",
    "https://vidsrc.cc",
    "https://vidsrc.net",
]

# Direct streaming sites
STREAMING_SITES = {
    'flixmomo': {
        'base': 'https://flixmomo.tv',
        'movie': '/movie/{imdb_id}',
        'tv': '/tv/{imdb_id}/{season}/{episode}'
    },
    'hydrahd': {
        'base': 'https://hydrahd.ru',
        'movie': '/movie/{imdb_id}',
        'tv': '/tv/{imdb_id}-{season}-{episode}'
    },
    'cineby': {
        'base': 'https://cineby.gd',
        'movie': '/movie/{imdb_id}',
        'tv': '/tv/{imdb_id}/{season}/{episode}'
    },
    'flickystream': {
        'base': 'https://flickystream.ru',
        'movie': '/movie/{imdb_id}',
        'tv': '/tv/{imdb_id}/{season}/{episode}'
    },
    'yflix': {
        'base': 'https://yflix.to',
        'movie': '/movie/{imdb_id}',
        'tv': '/tv/{imdb_id}/{season}/{episode}'
    },
    'gomovies': {
        'base': 'https://gomovies.gg',
        'search': '/search/{query}'
    },
    'utelevision': {
        'base': 'https://utelevision.to',
        'movie': '/movie/{imdb_id}',
        'tv': '/tv/{imdb_id}/{season}/{episode}'
    },
    'movieparadise': {
        'base': 'https://movieparadise.co',
        'search': '/search?q={query}'
    },
    'rlsbb': {
        'base': 'https://rlsbb.ru',
        'search': '/?s={query}'
    },
    'archive_disney': {
        'base': 'https://archive.org/download/disney_202105',
        'direct': True
    }
}

def _fetch_page(url, timeout=15, referer=None):
    """Fetch HTML page with better error handling"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    if referer:
        headers['Referer'] = referer
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as response:
            data = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                data = gzip.decompress(data)
            return data.decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log(f"Scraper error fetching {url}: {e}", xbmc.LOGWARNING)
        return ""

def _fetch_json(url, timeout=15, headers=None):
    """Fetch JSON from API"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    if headers:
        default_headers.update(headers)
    
    try:
        req = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f"API error for {url[:50]}: {e}", xbmc.LOGWARNING)
        return None

def _detect_quality(name):
    """Detect video quality from torrent name"""
    name_lower = name.lower()
    
    if any(q in name_lower for q in ['2160p', '4k', 'uhd', 'ultra.hd']):
        return '4K'
    elif any(q in name_lower for q in ['1080p', '1080i', 'fhd', 'fullhd', 'full.hd']):
        return '1080p'
    elif any(q in name_lower for q in ['720p', 'hd', 'hdtv', 'bdrip', 'brrip']):
        return '720p'
    elif any(q in name_lower for q in ['480p', 'dvdrip', 'dvd', 'sd', 'webrip', 'hdcam', 'cam']):
        return 'SD'
    else:
        if 'bluray' in name_lower or 'blu-ray' in name_lower:
            return '1080p'
        elif 'web-dl' in name_lower or 'webdl' in name_lower:
            return '1080p'
        return 'Unknown'

def _create_magnet(info_hash, name):
    """Create magnet link from info hash"""
    trackers = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://open.stealth.si:80/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://tracker.bittor.pw:1337/announce",
        "udp://public.popcorn-tracker.org:6969/announce",
        "udp://tracker.dler.org:6969/announce",
        "udp://exodus.desync.com:6969",
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.openbittorrent.com:6969/announce",
        "udp://p4p.arenabg.com:1337/announce",
    ]
    
    encoded_name = urllib.parse.quote(name)
    tracker_params = "&".join([f"tr={urllib.parse.quote(t)}" for t in trackers])
    
    return f"magnet:?xt=urn:btih:{info_hash}&dn={encoded_name}&{tracker_params}"

def _parse_stremio_streams(data, source_name):
    """Parse Stremio addon stream response"""
    results = []
    
    if not data or 'streams' not in data:
        return results
    
    for stream in data.get('streams', []):
        try:
            name = stream.get('name', '') or stream.get('title', 'Unknown')
            title = stream.get('title', '') or name
            
            # Get quality from name or title
            quality = _detect_quality(f"{name} {title}")
            
            # Parse size and seeds from title if available
            size = ''
            seeds = 0
            
            # Common patterns in Stremio stream titles
            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|gb|mb))', title)
            if size_match:
                size = size_match.group(1)
            
            seeds_match = re.search(r'(\d+)\s*(?:seeds?|seeders?|S)', title, re.IGNORECASE)
            if seeds_match:
                seeds = int(seeds_match.group(1))
            
            # Get the stream URL or magnet
            info_hash = stream.get('infoHash', '')
            url = stream.get('url', '')
            
            if info_hash:
                magnet = _create_magnet(info_hash, name)
                results.append({
                    'name': f"{name} - {title}" if title and title != name else name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': source_name,
                    'source_type': source_name.lower(),
                    'debrid': True
                })
            elif url:
                results.append({
                    'name': f"{name} - {title}" if title and title != name else name,
                    'stream_url': url,
                    'quality': quality,
                    'size': size,
                    'seeds': 0,
                    'source': source_name,
                    'source_type': source_name.lower(),
                    'debrid': False,
                    'direct_stream': True
                })
        except Exception as e:
            xbmc.log(f"Error parsing {source_name} stream: {e}", xbmc.LOGWARNING)
            continue
    
    return results

# ============== TORRENTIO ==============

def _search_torrentio(imdb_id, media_type='movie', season=None, episode=None):
    """Search Torrentio Stremio addon for streams"""
    results = []
    
    if not imdb_id:
        return results
    
    try:
        # Build the stream URL
        # Torrentio uses /stream/{type}/{id}.json format
        if media_type == 'movie':
            stream_id = imdb_id
            url = f"{TORRENTIO_BASE}/stream/movie/{stream_id}.json"
        else:
            # TV shows use format: imdb_id:season:episode
            stream_id = f"{imdb_id}:{season}:{episode}"
            url = f"{TORRENTIO_BASE}/stream/series/{stream_id}.json"
        
        xbmc.log(f"Torrentio URL: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=20)
        
        if data:
            results = _parse_stremio_streams(data, 'Torrentio')
            xbmc.log(f"Torrentio found {len(results)} streams", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Torrentio error: {e}", xbmc.LOGERROR)
    
    return results

# ============== MEDIAFUSION ==============

def _search_mediafusion(imdb_id, media_type='movie', season=None, episode=None):
    """Search MediaFusion Stremio addon for streams"""
    results = []
    
    if not imdb_id:
        return results
    
    try:
        # MediaFusion public endpoint
        # Uses same Stremio addon format
        if media_type == 'movie':
            url = f"{MEDIAFUSION_BASE}/stream/movie/{imdb_id}.json"
        else:
            stream_id = f"{imdb_id}:{season}:{episode}"
            url = f"{MEDIAFUSION_BASE}/stream/series/{stream_id}.json"
        
        xbmc.log(f"MediaFusion URL: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=20)
        
        if data:
            results = _parse_stremio_streams(data, 'MediaFusion')
            xbmc.log(f"MediaFusion found {len(results)} streams", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"MediaFusion error: {e}", xbmc.LOGERROR)
    
    return results

# ============== ORIONOID ==============

def _get_orionoid_key():
    """Get Orionoid API key from settings or use default"""
    user_key = ADDON.getSetting('orionoid_key')
    if user_key and len(user_key) > 10:
        return user_key
    return "LSEF93X9KDLB9MQUCKD9PMDQDCSB5PNA"

def _search_orionoid(query, media_type='movie', imdb_id=None, tmdb_id=None):
    """Search Orionoid API for torrent streams"""
    results = []
    api_key = _get_orionoid_key()
    
    try:
        params = {
            'keyapp': api_key,
            'mode': 'stream',
            'action': 'retrieve',
            'type': media_type,
            'streamtype': 'torrent',
            'limitcount': 50,
            'sortvalue': 'best',
        }
        
        if imdb_id:
            params['idimdb'] = imdb_id.replace('tt', '')
        elif tmdb_id:
            params['idtmdb'] = tmdb_id
        else:
            params['query'] = query
        
        url = f"https://api.orionoid.com?{urllib.parse.urlencode(params)}"
        
        xbmc.log(f"Orionoid search URL: {url[:100]}...", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=25)
        
        if not data:
            return results
        
        result_status = data.get('result', {})
        if result_status.get('status') != 'success':
            error = result_status.get('message', 'Unknown error')
            xbmc.log(f"Orionoid API error: {error}", xbmc.LOGWARNING)
            return results
        
        streams = data.get('data', {}).get('streams', [])
        
        for stream in streams:
            try:
                file_info = stream.get('file', {})
                video_info = stream.get('video', {})
                stream_info = stream.get('stream', {})
                
                name = file_info.get('name', 'Unknown')
                
                links = stream.get('links', [])
                magnet = None
                for link in links:
                    if isinstance(link, str) and link.startswith('magnet:'):
                        magnet = link
                        break
                
                if not magnet:
                    file_hash = file_info.get('hash')
                    if file_hash:
                        magnet = _create_magnet(file_hash, name)
                
                if not magnet:
                    continue
                
                quality = video_info.get('quality', '').upper()
                if quality in ['HD1080', 'FHD', '1080']:
                    quality = '1080p'
                elif quality in ['HD720', 'HD', '720']:
                    quality = '720p'
                elif quality in ['UHD', 'UHD4K', '4K', '2160']:
                    quality = '4K'
                elif quality in ['SD', 'CAM', 'SCR', '480']:
                    quality = 'SD'
                else:
                    quality = _detect_quality(name)
                
                size_bytes = file_info.get('size', 0)
                if size_bytes > 1073741824:
                    size = f"{size_bytes / 1073741824:.1f} GB"
                elif size_bytes > 1048576:
                    size = f"{size_bytes / 1048576:.0f} MB"
                else:
                    size = ''
                
                seeds = stream_info.get('seeds', 0)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Orionoid',
                    'source_type': 'orionoid',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing Orionoid stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"Orionoid found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Orionoid search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== YTS (Movies) ==============

def _search_yts(query, year=''):
    """Search YTS API for movies"""
    results = []
    
    try:
        search_query = f"{query} {year}".strip() if year else query
        url = f"https://yts.mx/api/v2/list_movies.json?query_term={urllib.parse.quote(search_query)}&limit=30"
        
        data = _fetch_json(url, timeout=15)
        
        if not data or data.get('status') != 'ok':
            return results
        
        movies = data.get('data', {}).get('movies', [])
        
        for movie in movies:
            torrents = movie.get('torrents', [])
            title = movie.get('title', 'Unknown')
            movie_year = movie.get('year', '')
            
            for torrent in torrents:
                quality = torrent.get('quality', 'Unknown')
                size = torrent.get('size', '')
                seeds = torrent.get('seeds', 0)
                info_hash = torrent.get('hash', '')
                
                if info_hash:
                    name = f"{title} ({movie_year}) [{quality}] - YTS"
                    magnet = _create_magnet(info_hash, name)
                    
                    results.append({
                        'name': name,
                        'magnet': magnet,
                        'quality': quality,
                        'size': size,
                        'seeds': seeds,
                        'source': 'YTS',
                        'source_type': 'torrent',
                        'debrid': True
                    })
        
        xbmc.log(f"YTS found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"YTS error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== 1337X ==============

def _search_1337x(query):
    """Search 1337x for torrents"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://1337x.to/search/{encoded_query}/1/"
        
        html = _fetch_page(url)
        if not html:
            return results
        
        pattern = r'<a href="(/torrent/\d+/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)
        
        for link, name in matches[:15]:
            name = name.strip()
            query_words = query.lower().split()[:3]
            if not any(word in name.lower() for word in query_words):
                continue
            
            results.append({
                'name': name,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': '1337x',
                'source_type': 'torrent',
                'debrid': True,
                'page_url': f"https://1337x.to{link}"
            })
        
        xbmc.log(f"1337x found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"1337x error: {e}", xbmc.LOGWARNING)
    
    return results

def _get_magnet_from_1337x(page_url):
    """Get magnet link from 1337x torrent page"""
    try:
        html = _fetch_page(page_url)
        if html:
            match = re.search(r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)', html)
            if match:
                return match.group(1)
    except Exception as e:
        xbmc.log(f"1337x magnet error: {e}", xbmc.LOGWARNING)
    return None

# ============== TORRENTGALAXY ==============

def _search_torrentgalaxy(query):
    """Search TorrentGalaxy for torrents"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://torrentgalaxy.to/torrents.php?search={encoded_query}"
        
        html = _fetch_page(url)
        if not html:
            return results
        
        magnet_pattern = r'(magnet:\?xt=urn:btih:[a-fA-F0-9]{40}[^"\'<>\s]*)'
        magnets = re.findall(magnet_pattern, html)
        
        for magnet in magnets[:15]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                continue
            
            query_words = query.lower().split()[:2]
            if not any(word in name.lower() for word in query_words):
                continue
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'TorrentGalaxy',
                'source_type': 'torrent',
                'debrid': True
            })
        
        xbmc.log(f"TorrentGalaxy found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"TorrentGalaxy error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== EZTV (TV Shows) ==============

def _search_eztv(imdb_id):
    """Search EZTV API for TV show torrents"""
    results = []
    
    if not imdb_id:
        return results
    
    try:
        clean_id = imdb_id.replace('tt', '')
        url = f"https://eztvx.to/api/get-torrents?imdb_id={clean_id}&limit=50"
        
        data = _fetch_json(url, timeout=15)
        
        if not data or 'torrents' not in data:
            return results
        
        for torrent in data.get('torrents', []):
            name = torrent.get('filename', torrent.get('title', 'Unknown'))
            info_hash = torrent.get('hash', '')
            size_bytes = torrent.get('size_bytes', 0)
            seeds = torrent.get('seeds', 0)
            
            if info_hash:
                magnet = _create_magnet(info_hash, name)
                
                if size_bytes > 1073741824:
                    size = f"{size_bytes / 1073741824:.1f} GB"
                elif size_bytes > 1048576:
                    size = f"{size_bytes / 1048576:.0f} MB"
                else:
                    size = ''
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': _detect_quality(name),
                    'size': size,
                    'seeds': seeds,
                    'source': 'EZTV',
                    'source_type': 'torrent',
                    'debrid': True
                })
        
        xbmc.log(f"EZTV found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"EZTV error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== DIRECT STREAMING SITES ==============

def _scrape_streaming_site(site_name, site_config, imdb_id=None, tmdb_id=None, title=None, 
                           media_type='movie', season=None, episode=None):
    """Scrape a streaming site for embed URLs"""
    results = []
    
    try:
        base_url = site_config.get('base', '')
        
        if site_config.get('direct'):
            # Direct archive links
            return results
        
        # Build URL based on media type
        if media_type == 'movie' and 'movie' in site_config:
            path = site_config['movie'].format(
                imdb_id=imdb_id or '',
                tmdb_id=tmdb_id or '',
                query=urllib.parse.quote_plus(title or '')
            )
        elif media_type == 'tv' and 'tv' in site_config:
            path = site_config['tv'].format(
                imdb_id=imdb_id or '',
                tmdb_id=tmdb_id or '',
                season=season or 1,
                episode=episode or 1
            )
        elif 'search' in site_config and title:
            path = site_config['search'].format(query=urllib.parse.quote_plus(title))
        else:
            return results
        
        url = f"{base_url}{path}"
        xbmc.log(f"Checking {site_name}: {url}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=10, referer=base_url)
        
        if not html or len(html) < 500:
            return results
        
        # Look for embed iframes or video sources
        iframe_patterns = [
            r'<iframe[^>]+src=["\']([^"\']+)["\']',
            r'data-src=["\']([^"\']+\.(?:php|html)[^"\']*)["\']',
            r'embed["\']?\s*:\s*["\']([^"\']+)["\']',
        ]
        
        m3u8_patterns = [
            r'(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)',
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        ]
        
        # Try to find m3u8 streams directly
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, html)
            for stream_url in matches[:3]:
                results.append({
                    'name': f"{site_name} Stream (Auto)",
                    'stream_url': stream_url,
                    'quality': '1080p',
                    'size': 'Stream',
                    'seeds': 0,
                    'source': site_name,
                    'source_type': 'direct',
                    'debrid': False,
                    'direct_stream': True
                })
        
        # If no direct streams, add embed URL
        if not results:
            for pattern in iframe_patterns:
                matches = re.findall(pattern, html)
                for embed_url in matches[:2]:
                    if 'google' in embed_url.lower() or 'facebook' in embed_url.lower():
                        continue
                    if not embed_url.startswith('http'):
                        embed_url = f"{base_url}{embed_url}" if embed_url.startswith('/') else f"{base_url}/{embed_url}"
                    
                    results.append({
                        'name': f"{site_name} Embed",
                        'stream_url': embed_url,
                        'quality': '720p',
                        'size': 'Stream',
                        'seeds': 0,
                        'source': site_name,
                        'source_type': 'direct',
                        'debrid': False,
                        'direct_stream': True
                    })
        
        # Add the page URL itself as fallback
        if not results and 'error' not in html.lower() and '404' not in html:
            results.append({
                'name': f"{site_name} Stream",
                'stream_url': url,
                'quality': '720p',
                'size': 'Stream',
                'seeds': 0,
                'source': site_name,
                'source_type': 'direct',
                'debrid': False,
                'direct_stream': True
            })
        
        if results:
            xbmc.log(f"{site_name} found {len(results)} streams", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"{site_name} scrape error: {e}", xbmc.LOGWARNING)
    
    return results

def _scrape_all_streaming_sites(imdb_id=None, tmdb_id=None, title=None, 
                                 media_type='movie', season=None, episode=None):
    """Scrape all configured streaming sites"""
    all_results = []
    
    sites_to_scrape = [
        ('FlixMomo', STREAMING_SITES.get('flixmomo', {})),
        ('HydraHD', STREAMING_SITES.get('hydrahd', {})),
        ('Cineby', STREAMING_SITES.get('cineby', {})),
        ('FlickyStream', STREAMING_SITES.get('flickystream', {})),
        ('YFlix', STREAMING_SITES.get('yflix', {})),
        ('GoMovies', STREAMING_SITES.get('gomovies', {})),
        ('UTelevision', STREAMING_SITES.get('utelevision', {})),
        ('MovieParadise', STREAMING_SITES.get('movieparadise', {})),
    ]
    
    for site_name, site_config in sites_to_scrape:
        if site_config:
            results = _scrape_streaming_site(
                site_name, site_config, imdb_id, tmdb_id, title,
                media_type, season, episode
            )
            all_results.extend(results)
    
    return all_results

# ============== RLSBB (DDL Site) ==============

def _search_rlsbb(query):
    """Search RLSBB for download links"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://rlsbb.ru/?s={encoded_query}"
        
        html = _fetch_page(url, timeout=15)
        if not html:
            return results
        
        # Find post links
        post_pattern = r'<a[^>]+href="(https://rlsbb\.ru/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(post_pattern, html)
        
        for post_url, post_title in matches[:10]:
            if query.lower().split()[0] not in post_title.lower():
                continue
            
            # Fetch post page to find download links
            post_html = _fetch_page(post_url, timeout=10)
            if post_html:
                # Find rapidgator and other DDL links
                ddl_patterns = [
                    r'(https?://rapidgator\.net/file/[^"\'<>\s]+)',
                    r'(https?://nitroflare\.com/view/[^"\'<>\s]+)',
                    r'(https?://1fichier\.com/\?[^"\'<>\s]+)',
                    r'(https?://uploaded\.net/file/[^"\'<>\s]+)',
                ]
                
                for pattern in ddl_patterns:
                    ddl_matches = re.findall(pattern, post_html)
                    for ddl_url in ddl_matches[:2]:
                        host = 'DDL'
                        if 'rapidgator' in ddl_url:
                            host = 'Rapidgator'
                        elif 'nitroflare' in ddl_url:
                            host = 'NitroFlare'
                        elif '1fichier' in ddl_url:
                            host = '1Fichier'
                        
                        results.append({
                            'name': f"{post_title[:60]} [{host}]",
                            'stream_url': ddl_url,
                            'quality': _detect_quality(post_title),
                            'size': '',
                            'seeds': 0,
                            'source': 'RLSBB',
                            'source_type': 'ddl',
                            'debrid': True,  # Most DDL hosts work with debrid
                            'direct_stream': False,
                            'ddl_link': True
                        })
        
        xbmc.log(f"RLSBB found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"RLSBB error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== VIDSRC ==============

def _extract_vidsrc_stream(embed_url, timeout=15):
    """Extract actual stream URL from VidSrc embed"""
    try:
        html = _fetch_page(embed_url, timeout=timeout)
        if not html:
            return None
        
        m3u8_patterns = [
            r'(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)',
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r"'file'\s*:\s*'([^']+\.m3u8[^']*)'",
            r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, html)
            if matches:
                for url in matches:
                    if 'master' in url.lower() or 'index' in url.lower() or url.endswith('.m3u8'):
                        return url
        
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html, re.DOTALL)
        
        for script in scripts:
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, script)
                if matches:
                    return matches[0]
        
        return None
        
    except Exception as e:
        xbmc.log(f"VidSrc extraction error: {e}", xbmc.LOGWARNING)
        return None

def _get_vidsrc_streams(tmdb_id, media_type='movie', season=None, episode=None, imdb_id=None):
    """Get VidSrc streaming links"""
    results = []
    
    content_id = imdb_id if imdb_id else tmdb_id
    
    for domain in VIDSRC_DOMAINS:
        try:
            if media_type == 'movie':
                embed_url = f"{domain}/embed/movie/{content_id}"
            else:
                embed_url = f"{domain}/embed/tv/{content_id}/{season}/{episode}"
            
            html = _fetch_page(embed_url, timeout=10)
            if not html or 'not found' in html.lower() or 'error' in html.lower():
                continue
            
            qualities = [
                ('1080p', 'HD'),
                ('720p', 'SD'),
                ('SD', 'Low')
            ]
            
            for quality, label in qualities:
                results.append({
                    'name': f"VidSrc Stream ({quality})",
                    'stream_url': embed_url,
                    'quality': quality,
                    'size': 'Stream',
                    'seeds': 0,
                    'source': 'VidSrc',
                    'source_type': 'vidsrc',
                    'debrid': False,
                    'direct_stream': True,
                    'domain': domain
                })
            
            xbmc.log(f"VidSrc found streams at {domain}", xbmc.LOGINFO)
            break
                
        except Exception as e:
            xbmc.log(f"VidSrc error for {domain}: {e}", xbmc.LOGWARNING)
            continue
    
    return results

# ============== SOURCE SETTINGS ==============

def _is_source_enabled(source_name):
    """Check if a source is enabled in settings"""
    setting_map = {
        'torrentio': 'enable_torrentio',
        'mediafusion': 'enable_mediafusion',
        'orionoid': 'enable_orionoid',
        'yts': 'enable_yts',
        'eztv': 'enable_eztv',
        '1337x': 'enable_1337x',
        'torrentgalaxy': 'enable_torrentgalaxy',
        'vidsrc': 'enable_vidsrc',
        'streaming_sites': 'enable_streaming_sites',
        'rlsbb': 'enable_rlsbb'
    }
    setting_id = setting_map.get(source_name.lower())
    if setting_id:
        return ADDON.getSetting(setting_id) != 'false'
    return True

# ============== MAIN SEARCH FUNCTIONS ==============

def search_movie(title, year='', tmdb_id=None, progress=None):
    """Search for movie sources across all scrapers"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} {year}".strip() if year else title
    
    # Get IMDB ID from TMDB for better search results
    imdb_id = None
    if tmdb_id:
        try:
            from resources.lib import tmdb
            external_ids = tmdb.get_external_ids('movie', tmdb_id)
            imdb_id = external_ids.get('imdb_id')
            xbmc.log(f"Got IMDB ID: {imdb_id} for TMDB: {tmdb_id}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Could not get IMDB ID: {e}", xbmc.LOGWARNING)
    
    # 1. Search Torrentio (Stremio addon)
    if _is_source_enabled('torrentio') and imdb_id:
        if progress:
            progress.update(3, "Searching Torrentio...")
        
        torrentio_results = _search_torrentio(imdb_id, 'movie')
        for r in torrentio_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
            elif r.get('direct_stream'):
                results.append(r)
    
    # 2. Search MediaFusion (Stremio addon)
    if _is_source_enabled('mediafusion') and imdb_id:
        if progress:
            progress.update(8, "Searching MediaFusion...")
        
        mf_results = _search_mediafusion(imdb_id, 'movie')
        for r in mf_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
            elif r.get('direct_stream'):
                results.append(r)
    
    # 3. Search Orionoid
    if _is_source_enabled('orionoid'):
        if progress:
            progress.update(15, "Searching Orionoid...")
        
        orion_results = _search_orionoid(search_query, 'movie', imdb_id, tmdb_id)
        for r in orion_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # 4. Search YTS (high quality movie torrents)
    if _is_source_enabled('yts'):
        if progress:
            progress.update(25, "Searching YTS...")
        
        yts_results = _search_yts(title, year)
        for r in yts_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # 5. Search 1337x
    if _is_source_enabled('1337x'):
        if progress:
            progress.update(35, "Searching 1337x...")
        
        try:
            found_1337x = _search_1337x(search_query)
            for r in found_1337x:
                results.append(r)
        except Exception as e:
            xbmc.log(f"1337x error: {e}", xbmc.LOGWARNING)
    
    # 6. Search TorrentGalaxy
    if _is_source_enabled('torrentgalaxy'):
        if progress:
            progress.update(45, "Searching TorrentGalaxy...")
        
        try:
            found_tgx = _search_torrentgalaxy(search_query)
            for r in found_tgx:
                if 'magnet' in r:
                    hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                    if hash_match:
                        h = hash_match.group(1).upper()
                        if h in seen_hashes:
                            continue
                        seen_hashes.add(h)
                results.append(r)
        except Exception as e:
            xbmc.log(f"TorrentGalaxy error: {e}", xbmc.LOGWARNING)
    
    # 7. Search RLSBB (DDL)
    if _is_source_enabled('rlsbb'):
        if progress:
            progress.update(55, "Searching RLSBB...")
        
        rlsbb_results = _search_rlsbb(search_query)
        results.extend(rlsbb_results)
    
    # 8. Add VidSrc direct streams
    if _is_source_enabled('vidsrc'):
        if progress:
            progress.update(65, "Getting VidSrc streams...")
        
        if tmdb_id or imdb_id:
            vidsrc_results = _get_vidsrc_streams(tmdb_id, 'movie', imdb_id=imdb_id)
            results.extend(vidsrc_results)
    
    # 9. Scrape additional streaming sites
    if _is_source_enabled('streaming_sites'):
        if progress:
            progress.update(75, "Checking streaming sites...")
        
        streaming_results = _scrape_all_streaming_sites(
            imdb_id=imdb_id, tmdb_id=tmdb_id, title=title, media_type='movie'
        )
        results.extend(streaming_results)
    
    # 10. Get magnets for 1337x results that need them
    if progress:
        progress.update(85, "Fetching magnet links...")
    
    for r in results:
        if 'magnet' not in r and 'page_url' in r:
            magnet = _get_magnet_from_1337x(r['page_url'])
            if magnet:
                r['magnet'] = magnet
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet, re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h in seen_hashes:
                        r['duplicate'] = True
                    else:
                        seen_hashes.add(h)
    
    # Filter out duplicates and torrents without magnets (keep direct streams)
    results = [r for r in results if (r.get('magnet') or r.get('direct_stream') or r.get('ddl_link')) and not r.get('duplicate')]
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
    xbmc.log(f"Total movie sources found: {len(results)}", xbmc.LOGINFO)
    return results

def search_episode(title, season, episode, tmdb_id=None, progress=None):
    """Search for TV episode sources"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} S{int(season):02d}E{int(episode):02d}"
    
    # Get IMDB ID from TMDB
    imdb_id = None
    if tmdb_id:
        try:
            from resources.lib import tmdb
            external_ids = tmdb.get_external_ids('tv', tmdb_id)
            imdb_id = external_ids.get('imdb_id')
            xbmc.log(f"Got TV IMDB ID: {imdb_id} for TMDB: {tmdb_id}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Could not get IMDB ID: {e}", xbmc.LOGWARNING)
    
    # 1. Search Torrentio
    if _is_source_enabled('torrentio') and imdb_id:
        if progress:
            progress.update(3, "Searching Torrentio...")
        
        torrentio_results = _search_torrentio(imdb_id, 'tv', season, episode)
        for r in torrentio_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
            elif r.get('direct_stream'):
                results.append(r)
    
    # 2. Search MediaFusion
    if _is_source_enabled('mediafusion') and imdb_id:
        if progress:
            progress.update(8, "Searching MediaFusion...")
        
        mf_results = _search_mediafusion(imdb_id, 'tv', season, episode)
        for r in mf_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
            elif r.get('direct_stream'):
                results.append(r)
    
    # 3. Search Orionoid
    if _is_source_enabled('orionoid'):
        if progress:
            progress.update(15, "Searching Orionoid...")
        
        orion_results = _search_orionoid(search_query, 'show', imdb_id, tmdb_id)
        for r in orion_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # 4. Search EZTV (specialized for TV)
    if _is_source_enabled('eztv'):
        if progress:
            progress.update(25, "Searching EZTV...")
        
        if imdb_id:
            eztv_results = _search_eztv(imdb_id)
            for r in eztv_results:
                name_lower = r.get('name', '').lower()
                ep_patterns = [
                    f's{int(season):02d}e{int(episode):02d}',
                    f'{season}x{int(episode):02d}',
                    f's{season}e{episode}',
                ]
                if any(pat in name_lower for pat in ep_patterns):
                    hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                    if hash_match:
                        h = hash_match.group(1).upper()
                        if h not in seen_hashes:
                            seen_hashes.add(h)
                            results.append(r)
    
    # 5. Search 1337x
    if _is_source_enabled('1337x'):
        if progress:
            progress.update(35, "Searching 1337x...")
        
        try:
            found_1337x = _search_1337x(search_query)
            for r in found_1337x:
                results.append(r)
        except Exception as e:
            xbmc.log(f"1337x error: {e}", xbmc.LOGWARNING)
    
    # 6. Search TorrentGalaxy
    if _is_source_enabled('torrentgalaxy'):
        if progress:
            progress.update(45, "Searching TorrentGalaxy...")
        
        try:
            found_tgx = _search_torrentgalaxy(search_query)
            for r in found_tgx:
                if 'magnet' in r:
                    hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                    if hash_match:
                        h = hash_match.group(1).upper()
                        if h in seen_hashes:
                            continue
                        seen_hashes.add(h)
                results.append(r)
        except Exception as e:
            xbmc.log(f"TorrentGalaxy error: {e}", xbmc.LOGWARNING)
    
    # 7. Search RLSBB (DDL)
    if _is_source_enabled('rlsbb'):
        if progress:
            progress.update(55, "Searching RLSBB...")
        
        rlsbb_results = _search_rlsbb(search_query)
        results.extend(rlsbb_results)
    
    # 8. Add VidSrc direct streams
    if _is_source_enabled('vidsrc'):
        if progress:
            progress.update(65, "Getting VidSrc streams...")
        
        if tmdb_id or imdb_id:
            vidsrc_results = _get_vidsrc_streams(tmdb_id, 'tv', season, episode, imdb_id)
            results.extend(vidsrc_results)
    
    # 9. Scrape additional streaming sites
    if _is_source_enabled('streaming_sites'):
        if progress:
            progress.update(75, "Checking streaming sites...")
        
        streaming_results = _scrape_all_streaming_sites(
            imdb_id=imdb_id, tmdb_id=tmdb_id, title=title,
            media_type='tv', season=season, episode=episode
        )
        results.extend(streaming_results)
    
    # 10. Get magnets for 1337x
    if progress:
        progress.update(85, "Fetching magnet links...")
    
    for r in results:
        if 'magnet' not in r and 'page_url' in r:
            magnet = _get_magnet_from_1337x(r['page_url'])
            if magnet:
                r['magnet'] = magnet
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet, re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h in seen_hashes:
                        r['duplicate'] = True
                    else:
                        seen_hashes.add(h)
    
    results = [r for r in results if (r.get('magnet') or r.get('direct_stream') or r.get('ddl_link')) and not r.get('duplicate')]
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
    xbmc.log(f"Total episode sources found: {len(results)}", xbmc.LOGINFO)
    return results

def sort_sources(sources, quality_filter=None):
    """Sort sources by quality and type, with optional filtering"""
    
    quality_order = {'4K': 0, '2160p': 0, '1080p': 1, '720p': 2, 'SD': 3, '480p': 3, 'Unknown': 4}
    
    if quality_filter and quality_filter != 'all':
        filter_map = {
            '4k': ['4K', '2160p'],
            '1080p': ['1080p'],
            '720p': ['720p'],
            'sd': ['SD', '480p']
        }
        allowed = filter_map.get(quality_filter.lower(), [])
        if allowed:
            sources = [s for s in sources if s.get('quality') in allowed]
    
    source_type_order = {'torrentio': 0, 'mediafusion': 0, 'orionoid': 1, 'torrent': 2, 'vidsrc': 3, 'direct': 4, 'ddl': 5}
    
    sorted_sources = sorted(
        sources,
        key=lambda x: (
            quality_order.get(x.get('quality', 'Unknown'), 4),
            source_type_order.get(x.get('source_type', 'torrent'), 2),
            -x.get('seeds', 0)
        )
    )
    
    return sorted_sources

def filter_sources_by_type(sources, source_type=None):
    """Filter sources by type"""
    if not source_type or source_type == 'all':
        return sources
    
    if source_type == 'debrid':
        return [s for s in sources if s.get('debrid')]
    elif source_type == 'vidsrc':
        return [s for s in sources if s.get('source_type') == 'vidsrc']
    elif source_type == 'orionoid':
        return [s for s in sources if s.get('source_type') == 'orionoid']
    elif source_type == 'torrent':
        return [s for s in sources if s.get('source_type') == 'torrent']
    elif source_type == 'torrentio':
        return [s for s in sources if s.get('source_type') == 'torrentio']
    elif source_type == 'mediafusion':
        return [s for s in sources if s.get('source_type') == 'mediafusion']
    elif source_type == 'direct':
        return [s for s in sources if s.get('source_type') in ['direct', 'vidsrc']]
    
    return sources
