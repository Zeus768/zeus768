# -*- coding: utf-8 -*-
"""
Torrent Scraper for Orion v3.3.0
Supports: Orionoid, Torrentio, MediaFusion, Jackettio, Comet,
PirateBay, YTS, EZTV, 1337x, Knaben, TorrentGalaxy, SolidTorrents,
BTDig, LimeTorrents, Nyaa, TorrentDownloads, RARBG,
Rutor, RuTracker, Kinozal, NNM-Club,
Torlock, GloDLS, MagnetDL, KickAss, TorrServer
"""

import urllib.request
import urllib.parse
import re
import ssl
import json
import base64
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
SSL_CONTEXT = ssl._create_unverified_context()

def _fetch_page(url, timeout=15, headers=None):
    """Fetch HTML page with better error handling"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    if headers:
        default_headers.update(headers)
    
    try:
        req = urllib.request.Request(url, headers=default_headers)
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
        'User-Agent': 'Orion Kodi Addon/3.0',
        'Accept': 'application/json',
    }
    if headers:
        default_headers.update(headers)
    
    try:
        req = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f"API error: {e}", xbmc.LOGWARNING)
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
    ]
    
    encoded_name = urllib.parse.quote(name)
    tracker_params = "&".join([f"tr={urllib.parse.quote(t)}" for t in trackers])
    
    return f"magnet:?xt=urn:btih:{info_hash}&dn={encoded_name}&{tracker_params}"

def _parse_size(size_str):
    """Parse size string to bytes for comparison"""
    try:
        size_str = size_str.upper().replace(' ', '')
        if 'GB' in size_str:
            return float(size_str.replace('GB', '')) * 1073741824
        elif 'MB' in size_str:
            return float(size_str.replace('MB', '')) * 1048576
        elif 'KB' in size_str:
            return float(size_str.replace('KB', '')) * 1024
    except:
        pass
    return 0

# ============== ORIONOID ==============

def _search_orionoid(query, media_type='movie', imdb_id=None):
    """Search Orionoid API with user's API key"""
    results = []
    
    api_key = ADDON.getSetting('orionoid_api_key')
    if not api_key:
        xbmc.log("Orionoid: No API key configured", xbmc.LOGINFO)
        return results
    
    try:
        params = {
            'keyapp': api_key,
            'mode': 'stream',
            'action': 'retrieve',
            'type': media_type,
            'streamtype': 'torrent',
            'limitcount': 30,
        }
        
        if imdb_id:
            params['idimdb'] = imdb_id.replace('tt', '')
        else:
            params['query'] = query
        
        url = f"https://api.orionoid.com?{urllib.parse.urlencode(params)}"
        
        xbmc.log(f"Orionoid search: {query}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=20)
        
        if not data:
            return results
        
        if data.get('result', {}).get('status') != 'success':
            error = data.get('result', {}).get('message', 'Unknown error')
            xbmc.log(f"Orionoid API error: {error}", xbmc.LOGWARNING)
            return results
        
        streams = data.get('data', {}).get('streams', [])
        
        for stream in streams:
            try:
                file_info = stream.get('file', {})
                video_info = stream.get('video', {})
                
                name = file_info.get('name', 'Unknown')
                
                links = stream.get('links', [])
                magnet = None
                for link in links:
                    if link.startswith('magnet:'):
                        magnet = link
                        break
                
                if not magnet:
                    file_hash = file_info.get('hash')
                    if file_hash:
                        magnet = _create_magnet(file_hash, name)
                
                if not magnet:
                    continue
                
                quality = video_info.get('quality', '').upper()
                if quality in ['HD1080', 'FHD']:
                    quality = '1080p'
                elif quality in ['HD720', 'HD']:
                    quality = '720p'
                elif quality in ['UHD', 'UHD4K', '4K']:
                    quality = '4K'
                elif quality in ['SD', 'CAM', 'SCR']:
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
                
                seeds = stream.get('stream', {}).get('seeds', 0)
                
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

# ============== TORRENTIO ==============

def _search_torrentio(imdb_id, media_type='movie', season=None, episode=None):
    """Search Torrentio public API"""
    results = []
    
    if not imdb_id:
        return results
    
    try:
        # Build Torrentio stream URL
        if media_type == 'movie':
            url = f"https://torrentio.strem.fun/stream/movie/{imdb_id}.json"
        else:
            url = f"https://torrentio.strem.fun/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"Torrentio search: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=20)
        
        if not data or 'streams' not in data:
            return results
        
        for stream in data.get('streams', []):
            try:
                title = stream.get('title', '')
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    # Try to extract from behaviorHints
                    behavior = stream.get('behaviorHints', {})
                    info_hash = behavior.get('bingeGroup', '').split('|')[-1] if behavior.get('bingeGroup') else ''
                
                if not info_hash:
                    continue
                
                # Parse title for name and metadata
                lines = title.split('\n')
                name = lines[0] if lines else 'Unknown'
                
                # Extract quality, size, seeds from title
                quality = _detect_quality(name)
                size = ''
                seeds = 0
                
                for line in lines:
                    if 'GB' in line or 'MB' in line:
                        size_match = re.search(r'([\d.]+\s*[GM]B)', line)
                        if size_match:
                            size = size_match.group(1)
                    if '👤' in line or 'Seeds' in line.lower():
                        seeds_match = re.search(r'(\d+)', line)
                        if seeds_match:
                            seeds = int(seeds_match.group(1))
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Torrentio',
                    'source_type': 'torrentio',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing Torrentio stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"Torrentio found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Torrentio search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== MEDIAFUSION ==============

def _search_mediafusion(imdb_id, media_type='movie', season=None, episode=None):
    """Search MediaFusion with user's manifest"""
    results = []
    
    manifest_url = ADDON.getSetting('mediafusion_manifest')
    if not manifest_url:
        return results
    
    try:
        # Extract base URL from manifest
        base_url = manifest_url.rsplit('/manifest.json', 1)[0]
        if not base_url:
            base_url = manifest_url.rsplit('/configure', 1)[0]
        
        # Build stream URL
        if media_type == 'movie':
            url = f"{base_url}/stream/movie/{imdb_id}.json"
        else:
            url = f"{base_url}/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"MediaFusion search: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=25)
        
        if not data or 'streams' not in data:
            return results
        
        for stream in data.get('streams', []):
            try:
                title = stream.get('title', stream.get('name', ''))
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    # Try to get from URL or behaviorHints
                    url_field = stream.get('url', '')
                    if 'magnet:' in url_field:
                        hash_match = re.search(r'btih:([a-fA-F0-9]{40})', url_field, re.IGNORECASE)
                        if hash_match:
                            info_hash = hash_match.group(1)
                
                if not info_hash:
                    continue
                
                lines = title.split('\n')
                name = lines[0] if lines else 'Unknown'
                
                quality = _detect_quality(name)
                size = ''
                seeds = 0
                
                for line in lines:
                    if 'GB' in line or 'MB' in line:
                        size_match = re.search(r'([\d.]+\s*[GM]B)', line)
                        if size_match:
                            size = size_match.group(1)
                    if '👤' in line or 'seed' in line.lower():
                        seeds_match = re.search(r'(\d+)', line)
                        if seeds_match:
                            seeds = int(seeds_match.group(1))
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'MediaFusion',
                    'source_type': 'mediafusion',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing MediaFusion stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"MediaFusion found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"MediaFusion search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== JACKETTIO ==============

def _search_jackettio(imdb_id, media_type='movie', season=None, episode=None):
    """Search Jackettio with user's manifest"""
    results = []
    
    manifest_url = ADDON.getSetting('jackettio_manifest')
    if not manifest_url:
        # Use public instance as fallback
        manifest_url = "https://jackettio.elfhosted.com/manifest.json"
    
    try:
        # Extract base URL from manifest
        base_url = manifest_url.rsplit('/manifest.json', 1)[0]
        
        # Build stream URL
        if media_type == 'movie':
            url = f"{base_url}/stream/movie/{imdb_id}.json"
        else:
            url = f"{base_url}/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"Jackettio search: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=25)
        
        if not data or 'streams' not in data:
            return results
        
        for stream in data.get('streams', []):
            try:
                title = stream.get('title', stream.get('name', ''))
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    url_field = stream.get('url', '')
                    if 'magnet:' in url_field:
                        hash_match = re.search(r'btih:([a-fA-F0-9]{40})', url_field, re.IGNORECASE)
                        if hash_match:
                            info_hash = hash_match.group(1)
                
                if not info_hash:
                    continue
                
                lines = title.split('\n')
                name = lines[0] if lines else 'Unknown'
                
                quality = _detect_quality(name)
                size = ''
                seeds = 0
                
                for line in lines:
                    if 'GB' in line or 'MB' in line:
                        size_match = re.search(r'([\d.]+\s*[GM]B)', line)
                        if size_match:
                            size = size_match.group(1)
                    if '👤' in line or 'seed' in line.lower():
                        seeds_match = re.search(r'(\d+)', line)
                        if seeds_match:
                            seeds = int(seeds_match.group(1))
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Jackettio',
                    'source_type': 'jackettio',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing Jackettio stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"Jackettio found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Jackettio search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== COCO SCRAPERS (1337x, TorrentDownloads, RARBG) ==============

def _parse_1337x(html, search_title):
    """Parse 1337x results"""
    results = []
    clean_search = search_title.lower()
    
    pattern = r'<a href="(/torrent/\d+/[^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html)
    
    for link, name in matches[:15]:
        if not any(word in name.lower() for word in clean_search.split()[:2]):
            continue
        
        results.append({
            'name': name.strip(),
            'quality': _detect_quality(name),
            'size': '',
            'seeds': 0,
            'source': '1337x',
            'source_type': 'coco',
            'debrid': True,
            'page_url': f"https://1337x.to{link}"
        })
    
    return results

def _get_magnet_from_1337x(page_url):
    """Get magnet link from 1337x torrent page"""
    html = _fetch_page(page_url)
    if html:
        match = re.search(r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)', html)
        if match:
            return match.group(1)
    return None

def _parse_torrentdownloads(html, search_title):
    """Parse TorrentDownloads results"""
    results = []
    clean_search = search_title.lower()
    
    magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
    magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
    
    for magnet in magnets[:20]:
        dn_match = re.search(r'dn=([^&]+)', magnet)
        if dn_match:
            name = urllib.parse.unquote_plus(dn_match.group(1))
        else:
            continue
        
        if not any(word in name.lower() for word in clean_search.split()[:2]):
            continue
        
        results.append({
            'name': name,
            'magnet': magnet,
            'quality': _detect_quality(name),
            'size': '',
            'seeds': 0,
            'source': 'TorrentDownloads',
            'source_type': 'coco',
            'debrid': True
        })
    
    return results

def _search_rarbg_alternatives(query):
    """Search RARBG alternative mirrors"""
    results = []
    
    mirrors = [
        'https://rargb.to',
        'https://therarbg.to',
    ]
    
    for mirror in mirrors:
        try:
            url = f"{mirror}/search/?search={urllib.parse.quote_plus(query)}"
            html = _fetch_page(url, timeout=10)
            
            if not html:
                continue
            
            # Parse magnet links
            magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
            magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
            
            for magnet in magnets[:15]:
                dn_match = re.search(r'dn=([^&]+)', magnet)
                name = urllib.parse.unquote_plus(dn_match.group(1)) if dn_match else 'Unknown'
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': _detect_quality(name),
                    'size': '',
                    'seeds': 0,
                    'source': 'RARBG',
                    'source_type': 'coco',
                    'debrid': True
                })
            
            if results:
                break
                
        except Exception as e:
            xbmc.log(f"RARBG mirror error: {e}", xbmc.LOGWARNING)
            continue
    
    return results

# ============== PIRATEBAY API ==============

def _search_piratebay(query):
    """Search PirateBay via apibay.org API"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://apibay.org/q.php?q={encoded_query}&cat=0"
        
        xbmc.log(f"PirateBay search: {query}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=15)
        
        if not data or (isinstance(data, list) and len(data) == 1 and data[0].get('id') == '0'):
            return results
        
        for item in data[:25]:
            try:
                name = item.get('name', '')
                info_hash = item.get('info_hash', '')
                size_bytes = int(item.get('size', 0))
                seeders = int(item.get('seeders', 0))
                
                if not info_hash or info_hash == '0' or not name:
                    continue
                
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
                    'seeds': seeders,
                    'source': 'PirateBay',
                    'source_type': 'coco',
                    'debrid': True
                })
            except Exception as e:
                continue
        
        xbmc.log(f"PirateBay found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"PirateBay error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== EZTV ==============

def _search_eztv(query, imdb_id=None):
    """Search EZTV API for TV shows"""
    results = []
    
    try:
        if imdb_id:
            imdb_num = imdb_id.replace('tt', '')
            url = f"https://eztv.re/api/get-torrents?imdb_id={imdb_num}&limit=30"
        else:
            url = f"https://eztv.re/api/get-torrents?limit=30"
        
        xbmc.log(f"EZTV search: {query}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=15)
        
        if not data or not data.get('torrents'):
            return results
        
        search_lower = query.lower()
        
        for item in data.get('torrents', [])[:25]:
            try:
                name = item.get('title', item.get('filename', ''))
                info_hash = item.get('hash', '')
                size_bytes = int(item.get('size_bytes', 0))
                seeders = int(item.get('seeds', 0))
                magnet_url = item.get('magnet_url', '')
                
                if not name:
                    continue
                
                if not any(w in name.lower() for w in search_lower.split()[:2]):
                    continue
                
                if magnet_url:
                    magnet = magnet_url
                elif info_hash:
                    magnet = _create_magnet(info_hash, name)
                else:
                    continue
                
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
                    'seeds': seeders,
                    'source': 'EZTV',
                    'source_type': 'coco',
                    'debrid': True
                })
            except Exception as e:
                continue
        
        xbmc.log(f"EZTV found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"EZTV error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== YTS ==============

def _search_yts(query):
    """Search YTS API for movies"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://yts.mx/api/v2/list_movies.json?query_term={encoded_query}&limit=20&sort_by=seeds"
        
        xbmc.log(f"YTS search: {query}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=15)
        
        if not data or data.get('status') != 'ok':
            return results
        
        movies = data.get('data', {}).get('movies', [])
        
        for movie in movies:
            try:
                movie_title = movie.get('title_long', movie.get('title', ''))
                
                for torrent in movie.get('torrents', []):
                    info_hash = torrent.get('hash', '')
                    quality = torrent.get('quality', '')
                    size = torrent.get('size', '')
                    seeds = int(torrent.get('seeds', 0))
                    codec = torrent.get('video_codec', '')
                    torrent_type = torrent.get('type', '')
                    
                    if not info_hash:
                        continue
                    
                    name = f"{movie_title} [{quality}] [{codec}] [{torrent_type}] - YTS"
                    magnet = _create_magnet(info_hash, name)
                    
                    q = quality if quality in ['2160p', '1080p', '720p'] else _detect_quality(quality)
                    
                    results.append({
                        'name': name,
                        'magnet': magnet,
                        'quality': q,
                        'size': size,
                        'seeds': seeds,
                        'source': 'YTS',
                        'source_type': 'coco',
                        'debrid': True
                    })
            except Exception as e:
                continue
        
        xbmc.log(f"YTS found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"YTS error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== KNABEN ==============

def _search_knaben(query):
    """Search Knaben torrent database API"""
    results = []
    
    try:
        url = "https://knaben.eu/api"
        post_data = json.dumps({
            "search_type": "torrent",
            "search_field": "title",
            "query": query,
            "order_by": "seeders",
            "order_direction": "desc",
            "hide_unsafe": True,
            "limit": 25
        }).encode('utf-8')
        
        xbmc.log(f"Knaben search: {query}", xbmc.LOGINFO)
        
        req = urllib.request.Request(url, data=post_data, headers={
            'User-Agent': 'Orion Kodi Addon/3.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if not data or 'hits' not in data:
            return results
        
        for item in data.get('hits', [])[:25]:
            try:
                hit = item.get('_source', item)
                name = hit.get('title', '')
                info_hash = hit.get('infohash', '')
                size_bytes = int(hit.get('size', 0))
                seeders = int(hit.get('seeders', 0))
                
                if not info_hash or not name:
                    continue
                
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
                    'seeds': seeders,
                    'source': 'Knaben',
                    'source_type': 'coco',
                    'debrid': True
                })
            except Exception as e:
                continue
        
        xbmc.log(f"Knaben found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Knaben error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== SOLIDTORRENTS ==============

def _search_solidtorrents(query):
    """Search SolidTorrents API"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://solidtorrents.to/api/v1/search?q={encoded_query}&category=video&sort=seeders"
        
        xbmc.log(f"SolidTorrents search: {query}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=15)
        
        if not data or 'results' not in data:
            return results
        
        for item in data.get('results', [])[:25]:
            try:
                name = item.get('title', '')
                info_hash = item.get('infohash', '')
                magnet_url = item.get('magnet', '')
                size_bytes = int(item.get('size', 0))
                
                swarm = item.get('swarm', {})
                seeders = int(swarm.get('seeders', 0)) if isinstance(swarm, dict) else 0
                
                if not name:
                    continue
                
                if magnet_url:
                    magnet = magnet_url
                elif info_hash:
                    magnet = _create_magnet(info_hash, name)
                else:
                    continue
                
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
                    'seeds': seeders,
                    'source': 'SolidTorrents',
                    'source_type': 'coco',
                    'debrid': True
                })
            except Exception as e:
                continue
        
        xbmc.log(f"SolidTorrents found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"SolidTorrents error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== BTDIG ==============

def _search_btdig(query):
    """Search BTDig torrent search engine"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://btdig.com/search?q={encoded_query}&order=0"
        
        xbmc.log(f"BTDig search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        # Parse results - BTDig has magnet links and info hashes
        pattern = r'magnet:\?xt=urn:btih:([a-fA-F0-9]{40})[^"\'<>\s]*'
        magnets = re.findall(pattern, html)
        
        # Also extract names
        name_pattern = r'<div class="one_result">.*?<div class="torrent_name"[^>]*>.*?<a[^>]*>([^<]+)</a>'
        names = re.findall(name_pattern, html, re.DOTALL)
        
        # Fallback: extract full magnet links
        full_magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        full_magnets = re.findall(full_magnet_pattern, html, re.IGNORECASE)
        
        search_lower = query.lower()
        
        for magnet in full_magnets[:20]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                continue
            
            if not any(w in name.lower() for w in search_lower.split()[:2]):
                continue
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'BTDig',
                'source_type': 'coco',
                'debrid': True
            })
        
        xbmc.log(f"BTDig found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"BTDig error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== LIMETORRENTS ==============

def _search_limetorrents(query):
    """Search LimeTorrents"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.limetorrents.lol/search/all/{encoded_query}/seeds/1/"
        
        xbmc.log(f"LimeTorrents search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        # Extract info hash links and names
        pattern = r'href="/torrent-download/([a-fA-F0-9]{40})[^"]*"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)
        
        # Fallback: extract magnet links directly
        magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
        
        search_lower = query.lower()
        
        for magnet in magnets[:20]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                continue
            
            if not any(w in name.lower() for w in search_lower.split()[:2]):
                continue
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'LimeTorrents',
                'source_type': 'coco',
                'debrid': True
            })
        
        xbmc.log(f"LimeTorrents found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"LimeTorrents error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== TORRENTGALAXY ==============

def _search_torrentgalaxy(query):
    """Search TorrentGalaxy"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://torrentgalaxy.to/torrents.php?search={encoded_query}&sort=seeders&order=desc"
        
        xbmc.log(f"TorrentGalaxy search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
        
        search_lower = query.lower()
        
        for magnet in magnets[:20]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                continue
            
            if not any(w in name.lower() for w in search_lower.split()[:2]):
                continue
            
            # Try to extract size from nearby HTML
            size = ''
            seeds = 0
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': size,
                'seeds': seeds,
                'source': 'TorrentGalaxy',
                'source_type': 'coco',
                'debrid': True
            })
        
        xbmc.log(f"TorrentGalaxy found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"TorrentGalaxy error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== NYAA (ANIME) ==============

def _search_nyaa(query):
    """Search Nyaa.si for anime torrents"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://nyaa.si/?f=0&c=0_0&q={encoded_query}&s=seeders&o=desc"
        
        xbmc.log(f"Nyaa search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
        
        for magnet in magnets[:20]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                continue
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'Nyaa',
                'source_type': 'coco',
                'debrid': True
            })
        
        xbmc.log(f"Nyaa found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Nyaa error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== COMET (STREMIO) ==============

def _search_comet(imdb_id, media_type='movie', season=None, episode=None):
    """Search Comet Stremio addon"""
    results = []
    
    if not imdb_id:
        return results
    
    try:
        base_url = "https://comet.elfhosted.com"
        
        if media_type == 'movie':
            url = f"{base_url}/stream/movie/{imdb_id}.json"
        else:
            url = f"{base_url}/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"Comet search: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=20)
        
        if not data or 'streams' not in data:
            return results
        
        for stream in data.get('streams', []):
            try:
                title = stream.get('title', '')
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    continue
                
                lines = title.split('\n')
                name = lines[0] if lines else 'Unknown'
                
                quality = _detect_quality(name)
                size = ''
                seeds = 0
                
                for line in lines:
                    if 'GB' in line or 'MB' in line:
                        size_match = re.search(r'([\d.]+\s*[GM]B)', line)
                        if size_match:
                            size = size_match.group(1)
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Comet',
                    'source_type': 'torrentio',
                    'debrid': True
                })
            except Exception as e:
                continue
        
        xbmc.log(f"Comet found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Comet error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== RUTOR (Russian Public Tracker) ==============

def _search_rutor(query):
    """Search Rutor.info - public Russian torrent tracker"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"http://rutor.info/search/0/0/010/0/{encoded_query}"
        
        xbmc.log(f"Rutor search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            # Try mirror
            url = f"http://rutor.is/search/0/0/010/0/{encoded_query}"
            html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        # Rutor has magnet links directly in the page
        magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
        
        # Extract sizes from table rows
        size_pattern = r'class="col-[^"]*"[^>]*>(\d+[\.,]\d+\s*[GMKT]B)</td>'
        sizes = re.findall(size_pattern, html, re.IGNORECASE)
        
        search_lower = query.lower()
        
        for i, magnet in enumerate(magnets[:25]):
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                # Try to extract from btih hash
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
                if hash_match:
                    name = f"Rutor-{hash_match.group(1)[:8]}"
                else:
                    continue
            
            size = sizes[i] if i < len(sizes) else ''
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': size,
                'seeds': 0,
                'source': 'Rutor',
                'source_type': 'russian',
                'debrid': True
            })
        
        xbmc.log(f"Rutor found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Rutor error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== RUTRACKER (Russian Private Tracker) ==============

def _search_rutracker(query):
    """Search RuTracker.org - requires login credentials in settings"""
    results = []
    
    username = ADDON.getSetting('rutracker_username')
    password = ADDON.getSetting('rutracker_password')
    
    if not username or not password:
        xbmc.log("RuTracker: No credentials configured", xbmc.LOGINFO)
        return results
    
    try:
        import http.cookiejar
        
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar),
            urllib.request.HTTPSHandler(context=SSL_CONTEXT)
        )
        
        # Login
        login_url = "https://rutracker.org/forum/login.php"
        login_data = urllib.parse.urlencode({
            'login_username': username,
            'login_password': password,
            'login': '%C2%F5%EE%E4'
        }).encode('utf-8')
        
        login_req = urllib.request.Request(login_url, data=login_data, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://rutracker.org/forum/index.php'
        })
        
        opener.open(login_req, timeout=15)
        
        # Search
        search_url = "https://rutracker.org/forum/tracker.php"
        search_data = urllib.parse.urlencode({
            'nm': query,
            'o': '10',  # Sort by seeds
            's': '2'    # Descending
        }).encode('utf-8')
        
        search_req = urllib.request.Request(search_url, data=search_data, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://rutracker.org/forum/tracker.php'
        })
        
        xbmc.log(f"RuTracker search: {query}", xbmc.LOGINFO)
        
        response = opener.open(search_req, timeout=20)
        html = response.read().decode('windows-1251', errors='ignore')
        
        if not html:
            return results
        
        # Parse results - extract topic IDs and names
        # RuTracker format: <a ... href="viewtopic.php?t=TOPIC_ID">NAME</a>
        row_pattern = r'<a[^>]*data-topic_id="(\d+)"[^>]*class="[^"]*tLink[^"]*"[^>]*>([^<]+)</a>'
        matches = re.findall(row_pattern, html)
        
        # Extract sizes
        size_pattern = r'<td class="[^"]*tor-size[^"]*"[^>]*>\s*<u>(\d+)</u>'
        size_matches = re.findall(size_pattern, html)
        
        # Extract seeds  
        seed_pattern = r'<td class="[^"]*seed[^"]*"[^>]*>\s*<b>(\d+)</b>'
        seed_matches = re.findall(seed_pattern, html)
        
        for i, (topic_id, name) in enumerate(matches[:20]):
            name = name.strip()
            
            # Get magnet link from topic page
            try:
                topic_url = f"https://rutracker.org/forum/viewtopic.php?t={topic_id}"
                topic_req = urllib.request.Request(topic_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                topic_html = opener.open(topic_req, timeout=10).read().decode('windows-1251', errors='ignore')
                
                magnet_match = re.search(r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)', topic_html)
                if not magnet_match:
                    continue
                
                magnet = magnet_match.group(1)
                
                size = ''
                if i < len(size_matches):
                    try:
                        size_bytes = int(size_matches[i])
                        if size_bytes > 1073741824:
                            size = f"{size_bytes / 1073741824:.1f} GB"
                        elif size_bytes > 1048576:
                            size = f"{size_bytes / 1048576:.0f} MB"
                    except:
                        pass
                
                seeds = int(seed_matches[i]) if i < len(seed_matches) else 0
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': _detect_quality(name),
                    'size': size,
                    'seeds': seeds,
                    'source': 'RuTracker',
                    'source_type': 'russian',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"RuTracker topic error: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"RuTracker found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"RuTracker error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== KINOZAL (Russian Movie Tracker) ==============

def _search_kinozal(query):
    """Search Kinozal.tv - Russian movie/TV tracker, requires login"""
    results = []
    
    username = ADDON.getSetting('kinozal_username')
    password = ADDON.getSetting('kinozal_password')
    
    if not username or not password:
        xbmc.log("Kinozal: No credentials configured", xbmc.LOGINFO)
        return results
    
    try:
        import http.cookiejar
        
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar),
            urllib.request.HTTPSHandler(context=SSL_CONTEXT)
        )
        
        # Login
        login_url = "https://kinozal.tv/takelogin.php"
        login_data = urllib.parse.urlencode({
            'username': username,
            'password': password
        }).encode('utf-8')
        
        login_req = urllib.request.Request(login_url, data=login_data, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://kinozal.tv/'
        })
        
        opener.open(login_req, timeout=15)
        
        # Search
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://kinozal.tv/browse.php?s={encoded_query}&g=0&c=0&v=0&d=0&w=0&t=0&f=0"
        
        search_req = urllib.request.Request(search_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        xbmc.log(f"Kinozal search: {query}", xbmc.LOGINFO)
        
        response = opener.open(search_req, timeout=20)
        html = response.read().decode('windows-1251', errors='ignore')
        
        if not html:
            return results
        
        # Parse results
        row_pattern = r'<a[^>]*href="/details\.php\?id=(\d+)"[^>]*>([^<]+)</a>'
        matches = re.findall(row_pattern, html)
        
        for topic_id, name in matches[:15]:
            name = name.strip()
            
            try:
                # Get magnet from details page
                details_url = f"https://kinozal.tv/details.php?id={topic_id}"
                details_req = urllib.request.Request(details_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                details_html = opener.open(details_req, timeout=10).read().decode('windows-1251', errors='ignore')
                
                # Extract info hash
                hash_match = re.search(r'([a-fA-F0-9]{40})', details_html)
                magnet_match = re.search(r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)', details_html)
                
                if magnet_match:
                    magnet = magnet_match.group(1)
                elif hash_match:
                    magnet = _create_magnet(hash_match.group(1), name)
                else:
                    continue
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': _detect_quality(name),
                    'size': '',
                    'seeds': 0,
                    'source': 'Kinozal',
                    'source_type': 'russian',
                    'debrid': True
                })
                
            except Exception as e:
                continue
        
        xbmc.log(f"Kinozal found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Kinozal error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== NONAMECLUB (Russian Public Tracker) ==============

def _search_nnmclub(query):
    """Search NoNaMe Club - Russian torrent tracker"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://nnmclub.to/forum/tracker.php?nm={encoded_query}"
        
        xbmc.log(f"NNM-Club search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
        
        for magnet in magnets[:20]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
                name = f"NNM-{hash_match.group(1)[:8]}" if hash_match else 'Unknown'
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'NNM-Club',
                'source_type': 'russian',
                'debrid': True
            })
        
        xbmc.log(f"NNM-Club found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"NNM-Club error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== TORLOCK ==============

def _search_torlock(query):
    """Search Torlock torrent site"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.torlock.com/all/torrents/{encoded_query}.html"
        
        xbmc.log(f"Torlock search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        # Extract torrent links with info hashes
        # Torlock uses /torrent/ID/name.html format
        link_pattern = r'<a[^>]*href="/torrent/(\d+)/([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(link_pattern, html)
        
        search_lower = query.lower()
        
        for torrent_id, slug, name in matches[:20]:
            name = name.strip()
            if not any(w in name.lower() for w in search_lower.split()[:2]):
                continue
            
            # Get magnet from torrent page
            try:
                torrent_url = f"https://www.torlock.com/torrent/{torrent_id}/{slug}"
                torrent_html = _fetch_page(torrent_url, timeout=10)
                if torrent_html:
                    magnet_match = re.search(r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)', torrent_html)
                    if magnet_match:
                        results.append({
                            'name': name,
                            'magnet': magnet_match.group(1),
                            'quality': _detect_quality(name),
                            'size': '',
                            'seeds': 0,
                            'source': 'Torlock',
                            'source_type': 'coco',
                            'debrid': True
                        })
            except:
                continue
        
        # Fallback: directly extract magnets
        if not results:
            magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
            magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
            for magnet in magnets[:15]:
                dn_match = re.search(r'dn=([^&]+)', magnet)
                if dn_match:
                    name = urllib.parse.unquote_plus(dn_match.group(1))
                    if any(w in name.lower() for w in search_lower.split()[:2]):
                        results.append({
                            'name': name,
                            'magnet': magnet,
                            'quality': _detect_quality(name),
                            'size': '',
                            'seeds': 0,
                            'source': 'Torlock',
                            'source_type': 'coco',
                            'debrid': True
                        })
        
        xbmc.log(f"Torlock found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Torlock error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== GLODLS / GLOTORRENTS ==============

def _search_glodls(query):
    """Search GloTorrents/GloDLS"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://glodls.to/search_results.php?search={encoded_query}&cat=0&incldead=0&inclexternal=0&lang=0&sort=seeders&order=desc"
        
        xbmc.log(f"GloDLS search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
        
        search_lower = query.lower()
        
        for magnet in magnets[:20]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                continue
            
            if not any(w in name.lower() for w in search_lower.split()[:2]):
                continue
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'GloDLS',
                'source_type': 'coco',
                'debrid': True
            })
        
        xbmc.log(f"GloDLS found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"GloDLS error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== MAGNETDL ==============

def _search_magnetdl(query):
    """Search MagnetDL torrent aggregator"""
    results = []
    
    try:
        # MagnetDL uses first letter of query in URL
        clean_query = query.strip().lower()
        first_letter = clean_query[0] if clean_query else 'a'
        encoded_query = clean_query.replace(' ', '-')
        url = f"https://www.magnetdl.com/{first_letter}/{encoded_query}/"
        
        xbmc.log(f"MagnetDL search: {query}", xbmc.LOGINFO)
        
        html = _fetch_page(url, timeout=15)
        
        if not html:
            return results
        
        magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
        magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
        
        for magnet in magnets[:20]:
            dn_match = re.search(r'dn=([^&]+)', magnet)
            if dn_match:
                name = urllib.parse.unquote_plus(dn_match.group(1))
            else:
                continue
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'MagnetDL',
                'source_type': 'coco',
                'debrid': True
            })
        
        xbmc.log(f"MagnetDL found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"MagnetDL error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== KICKASS TORRENTS ==============

def _search_kickass(query):
    """Search KickAss Torrents mirrors"""
    results = []
    
    mirrors = [
        'https://kickasstorrents.to',
        'https://katcr.to',
        'https://kat.am',
    ]
    
    for mirror in mirrors:
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"{mirror}/usearch/{encoded_query}/"
            
            xbmc.log(f"KickAss search: {url}", xbmc.LOGINFO)
            
            html = _fetch_page(url, timeout=10)
            
            if not html:
                continue
            
            magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
            magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
            
            search_lower = query.lower()
            
            for magnet in magnets[:20]:
                dn_match = re.search(r'dn=([^&]+)', magnet)
                if dn_match:
                    name = urllib.parse.unquote_plus(dn_match.group(1))
                else:
                    continue
                
                if not any(w in name.lower() for w in search_lower.split()[:2]):
                    continue
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': _detect_quality(name),
                    'size': '',
                    'seeds': 0,
                    'source': 'KickAss',
                    'source_type': 'coco',
                    'debrid': True
                })
            
            if results:
                break
                
        except Exception as e:
            xbmc.log(f"KickAss mirror error: {e}", xbmc.LOGWARNING)
            continue
    
    xbmc.log(f"KickAss found {len(results)} results", xbmc.LOGINFO)
    return results

# ============== TORRSERVER INTEGRATION ==============

def _search_torrserver(query):
    """Search through TorrServer instance if configured"""
    results = []
    
    server_url = ADDON.getSetting('torrserver_url')
    if not server_url:
        return results
    
    server_url = server_url.rstrip('/')
    
    try:
        xbmc.log(f"TorrServer search: {query}", xbmc.LOGINFO)
        
        # TorrServer API - list torrents
        list_url = f"{server_url}/torrents"
        
        post_data = json.dumps({
            'action': 'list'
        }).encode('utf-8')
        
        req = urllib.request.Request(list_url, data=post_data, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if not data:
            return results
        
        search_lower = query.lower()
        
        for torrent in data:
            name = torrent.get('title', torrent.get('name', ''))
            info_hash = torrent.get('hash', '')
            
            if not name or not info_hash:
                continue
            
            if not any(w in name.lower() for w in search_lower.split()[:2]):
                continue
            
            magnet = _create_magnet(info_hash, name)
            
            # TorrServer can stream directly
            stream_url = f"{server_url}/stream?link={info_hash}&index=0&play"
            
            results.append({
                'name': f"[TorrServer] {name}",
                'magnet': magnet,
                'stream_url': stream_url,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'TorrServer',
                'source_type': 'torrserver',
                'debrid': False
            })
        
        xbmc.log(f"TorrServer found {len(results)} results", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"TorrServer error: {e}", xbmc.LOGWARNING)
    
    return results

def _torrserver_add_and_play(magnet_or_hash, server_url=None):
    """Add a torrent to TorrServer and get stream URL"""
    if not server_url:
        server_url = ADDON.getSetting('torrserver_url')
    
    if not server_url:
        return None
    
    server_url = server_url.rstrip('/')
    
    try:
        # Add torrent to TorrServer
        add_url = f"{server_url}/torrents"
        
        if magnet_or_hash.startswith('magnet:'):
            link = magnet_or_hash
        else:
            link = f"magnet:?xt=urn:btih:{magnet_or_hash}"
        
        post_data = json.dumps({
            'action': 'add',
            'link': link,
            'title': '',
            'poster': '',
            'save_to_db': False
        }).encode('utf-8')
        
        req = urllib.request.Request(add_url, data=post_data, headers={
            'Content-Type': 'application/json',
        })
        
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        info_hash = data.get('hash', '')
        if info_hash:
            return f"{server_url}/stream?link={info_hash}&index=0&play"
        
    except Exception as e:
        xbmc.log(f"TorrServer add error: {e}", xbmc.LOGWARNING)
    
    return None

# ============== MAIN SEARCH FUNCTIONS ==============

def get_imdb_from_tmdb(tmdb_id, media_type='movie'):
    """Get IMDB ID from TMDB ID"""
    from resources.lib import tmdb
    
    try:
        ids = tmdb.get_external_ids(media_type, tmdb_id)
        return ids.get('imdb_id', '')
    except:
        return ''

def search_movie(title, year='', tmdb_id=None, progress=None):
    """Search for movie sources across all enabled scrapers"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} {year}".strip() if year else title
    
    # Get IMDB ID for stremio-based scrapers
    imdb_id = None
    if tmdb_id:
        imdb_id = get_imdb_from_tmdb(tmdb_id, 'movie')
    
    scraper_mode = int(ADDON.getSetting('scraper_mode') or 0)
    
    # ORION SCRAPERS MODE
    if scraper_mode == 0:
        # 1. Orionoid
        if ADDON.getSetting('orionoid_enabled') == 'true':
            if progress:
                progress.update(10, "Searching Orionoid...")
            
            orion_results = _search_orionoid(search_query, 'movie', imdb_id)
            for r in orion_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 2. Torrentio
        if ADDON.getSetting('torrentio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(30, "Searching Torrentio...")
            
            torrentio_results = _search_torrentio(imdb_id, 'movie')
            for r in torrentio_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 3. MediaFusion
        if ADDON.getSetting('mediafusion_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(50, "Searching MediaFusion...")
            
            mf_results = _search_mediafusion(imdb_id, 'movie')
            for r in mf_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 4. Jackettio
        if ADDON.getSetting('jackettio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(70, "Searching Jackettio...")
            
            jk_results = _search_jackettio(imdb_id, 'movie')
            for r in jk_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # COCO SCRAPERS MODE
    else:
        # 1. PirateBay API
        if ADDON.getSetting('coco_piratebay') != 'false':
            if progress:
                progress.update(10, "Searching PirateBay...")
            pb_results = _search_piratebay(search_query)
            for r in pb_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 2. YTS (movies only)
        if ADDON.getSetting('coco_yts') != 'false':
            if progress:
                progress.update(20, "Searching YTS...")
            yts_results = _search_yts(search_query)
            for r in yts_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 3. 1337x
        if ADDON.getSetting('coco_1337x') != 'false':
            if progress:
                progress.update(30, "Searching 1337x...")
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://1337x.to/search/{query}/1/"
                html = _fetch_page(url)
                if html:
                    found = _parse_1337x(html, search_query)
                    for r in found:
                        results.append(r)
            except Exception as e:
                xbmc.log(f"1337x error: {e}", xbmc.LOGWARNING)
        
        # 4. Knaben
        if ADDON.getSetting('coco_knaben') != 'false':
            if progress:
                progress.update(40, "Searching Knaben...")
            knaben_results = _search_knaben(search_query)
            for r in knaben_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 5. TorrentGalaxy
        if ADDON.getSetting('coco_torrentgalaxy') != 'false':
            if progress:
                progress.update(50, "Searching TorrentGalaxy...")
            tg_results = _search_torrentgalaxy(search_query)
            for r in tg_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 6. SolidTorrents
        if ADDON.getSetting('coco_solidtorrents') != 'false':
            if progress:
                progress.update(55, "Searching SolidTorrents...")
            st_results = _search_solidtorrents(search_query)
            for r in st_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 7. LimeTorrents
        if ADDON.getSetting('coco_limetorrents') != 'false':
            if progress:
                progress.update(60, "Searching LimeTorrents...")
            lt_results = _search_limetorrents(search_query)
            for r in lt_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 8. BTDig
        if ADDON.getSetting('coco_btdig') != 'false':
            if progress:
                progress.update(65, "Searching BTDig...")
            btdig_results = _search_btdig(search_query)
            for r in btdig_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 9. TorrentDownloads
        if ADDON.getSetting('coco_torrentdownloads') != 'false':
            if progress:
                progress.update(70, "Searching TorrentDownloads...")
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://www.torrentdownloads.pro/search/?search={query}"
                html = _fetch_page(url)
                if html:
                    found = _parse_torrentdownloads(html, search_query)
                    for r in found:
                        if 'magnet' in r:
                            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                            if hash_match:
                                h = hash_match.group(1).upper()
                                if h in seen_hashes:
                                    continue
                                seen_hashes.add(h)
                        results.append(r)
            except Exception as e:
                xbmc.log(f"TorrentDownloads error: {e}", xbmc.LOGWARNING)
        
        # 10. RARBG
        if ADDON.getSetting('coco_rarbg') != 'false':
            if progress:
                progress.update(75, "Searching RARBG...")
            rarbg_results = _search_rarbg_alternatives(search_query)
            for r in rarbg_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # Also search Comet if IMDB is available (works in both modes)
    if imdb_id and ADDON.getSetting('comet_enabled') != 'false':
        if progress:
            progress.update(78, "Searching Comet...")
        comet_results = _search_comet(imdb_id, 'movie')
        for r in comet_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # Russian torrent sites (work in both modes)
    if ADDON.getSetting('rutor_enabled') != 'false':
        if progress:
            progress.update(80, "Searching Rutor...")
        rutor_results = _search_rutor(search_query)
        for r in rutor_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('rutracker_enabled') != 'false':
        if progress:
            progress.update(82, "Searching RuTracker...")
        rt_results = _search_rutracker(search_query)
        for r in rt_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('kinozal_enabled') != 'false':
        if progress:
            progress.update(83, "Searching Kinozal...")
        kz_results = _search_kinozal(search_query)
        for r in kz_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('nnmclub_enabled') != 'false':
        if progress:
            progress.update(84, "Searching NNM-Club...")
        nnm_results = _search_nnmclub(search_query)
        for r in nnm_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # Additional torrent sites (work in both modes)
    if ADDON.getSetting('torlock_enabled') != 'false':
        if progress:
            progress.update(85, "Searching Torlock...")
        tl_results = _search_torlock(search_query)
        for r in tl_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('glodls_enabled') != 'false':
        if progress:
            progress.update(86, "Searching GloDLS...")
        gl_results = _search_glodls(search_query)
        for r in gl_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('magnetdl_enabled') != 'false':
        if progress:
            progress.update(87, "Searching MagnetDL...")
        md_results = _search_magnetdl(search_query)
        for r in md_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('kickass_enabled') != 'false':
        if progress:
            progress.update(88, "Searching KickAss...")
        ka_results = _search_kickass(search_query)
        for r in ka_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # TorrServer (local library search)
    if ADDON.getSetting('torrserver_url'):
        if progress:
            progress.update(89, "Searching TorrServer...")
        ts_results = _search_torrserver(search_query)
        for r in ts_results:
            results.append(r)
    
    # Get magnets for results that need them (1337x)
    if progress:
        progress.update(90, "Fetching magnet links...")
    
    for r in results:
        if 'magnet' not in r and 'page_url' in r:
            magnet = _get_magnet_from_1337x(r['page_url'])
            if magnet:
                r['magnet'] = magnet
    
    # Filter out results without magnets
    results = [r for r in results if r.get('magnet')]
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
    return results

def search_episode(title, season, episode, tmdb_id=None, progress=None):
    """Search for TV episode sources across all enabled scrapers"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} S{int(season):02d}E{int(episode):02d}"
    
    # Get IMDB ID for stremio-based scrapers
    imdb_id = None
    if tmdb_id:
        imdb_id = get_imdb_from_tmdb(tmdb_id, 'tv')
    
    scraper_mode = int(ADDON.getSetting('scraper_mode') or 0)
    
    # ORION SCRAPERS MODE
    if scraper_mode == 0:
        # 1. Orionoid
        if ADDON.getSetting('orionoid_enabled') == 'true':
            if progress:
                progress.update(10, "Searching Orionoid...")
            
            orion_results = _search_orionoid(search_query, 'show', imdb_id)
            for r in orion_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 2. Torrentio
        if ADDON.getSetting('torrentio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(30, "Searching Torrentio...")
            
            torrentio_results = _search_torrentio(imdb_id, 'tv', season, episode)
            for r in torrentio_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 3. MediaFusion
        if ADDON.getSetting('mediafusion_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(50, "Searching MediaFusion...")
            
            mf_results = _search_mediafusion(imdb_id, 'tv', season, episode)
            for r in mf_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 4. Jackettio
        if ADDON.getSetting('jackettio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(70, "Searching Jackettio...")
            
            jk_results = _search_jackettio(imdb_id, 'tv', season, episode)
            for r in jk_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # COCO SCRAPERS MODE
    else:
        # 1. PirateBay API
        if ADDON.getSetting('coco_piratebay') != 'false':
            if progress:
                progress.update(10, "Searching PirateBay...")
            pb_results = _search_piratebay(search_query)
            for r in pb_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 2. EZTV (TV specific)
        if ADDON.getSetting('coco_eztv') != 'false':
            if progress:
                progress.update(20, "Searching EZTV...")
            eztv_results = _search_eztv(search_query, imdb_id)
            for r in eztv_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 3. 1337x
        if ADDON.getSetting('coco_1337x') != 'false':
            if progress:
                progress.update(30, "Searching 1337x...")
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://1337x.to/search/{query}/1/"
                html = _fetch_page(url)
                if html:
                    found = _parse_1337x(html, search_query)
                    for r in found:
                        results.append(r)
            except Exception as e:
                xbmc.log(f"1337x error: {e}", xbmc.LOGWARNING)
        
        # 4. Knaben
        if ADDON.getSetting('coco_knaben') != 'false':
            if progress:
                progress.update(40, "Searching Knaben...")
            knaben_results = _search_knaben(search_query)
            for r in knaben_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 5. TorrentGalaxy
        if ADDON.getSetting('coco_torrentgalaxy') != 'false':
            if progress:
                progress.update(50, "Searching TorrentGalaxy...")
            tg_results = _search_torrentgalaxy(search_query)
            for r in tg_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 6. SolidTorrents
        if ADDON.getSetting('coco_solidtorrents') != 'false':
            if progress:
                progress.update(55, "Searching SolidTorrents...")
            st_results = _search_solidtorrents(search_query)
            for r in st_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 7. LimeTorrents
        if ADDON.getSetting('coco_limetorrents') != 'false':
            if progress:
                progress.update(60, "Searching LimeTorrents...")
            lt_results = _search_limetorrents(search_query)
            for r in lt_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 8. BTDig
        if ADDON.getSetting('coco_btdig') != 'false':
            if progress:
                progress.update(65, "Searching BTDig...")
            btdig_results = _search_btdig(search_query)
            for r in btdig_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 9. TorrentDownloads
        if ADDON.getSetting('coco_torrentdownloads') != 'false':
            if progress:
                progress.update(70, "Searching TorrentDownloads...")
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://www.torrentdownloads.pro/search/?search={query}"
                html = _fetch_page(url)
                if html:
                    found = _parse_torrentdownloads(html, search_query)
                    for r in found:
                        if 'magnet' in r:
                            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                            if hash_match:
                                h = hash_match.group(1).upper()
                                if h in seen_hashes:
                                    continue
                                seen_hashes.add(h)
                        results.append(r)
            except Exception as e:
                xbmc.log(f"TorrentDownloads error: {e}", xbmc.LOGWARNING)
        
        # 10. RARBG
        if ADDON.getSetting('coco_rarbg') != 'false':
            if progress:
                progress.update(75, "Searching RARBG...")
            rarbg_results = _search_rarbg_alternatives(search_query)
            for r in rarbg_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 11. Nyaa (anime)
        if ADDON.getSetting('coco_nyaa') != 'false':
            if progress:
                progress.update(78, "Searching Nyaa...")
            nyaa_results = _search_nyaa(search_query)
            for r in nyaa_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # Also search Comet if IMDB is available (works in both modes)
    if imdb_id and ADDON.getSetting('comet_enabled') != 'false':
        if progress:
            progress.update(78, "Searching Comet...")
        comet_results = _search_comet(imdb_id, 'tv', season, episode)
        for r in comet_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # Russian torrent sites (work in both modes)
    if ADDON.getSetting('rutor_enabled') != 'false':
        if progress:
            progress.update(80, "Searching Rutor...")
        rutor_results = _search_rutor(search_query)
        for r in rutor_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('rutracker_enabled') != 'false':
        if progress:
            progress.update(82, "Searching RuTracker...")
        rt_results = _search_rutracker(search_query)
        for r in rt_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('kinozal_enabled') != 'false':
        if progress:
            progress.update(83, "Searching Kinozal...")
        kz_results = _search_kinozal(search_query)
        for r in kz_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('nnmclub_enabled') != 'false':
        if progress:
            progress.update(84, "Searching NNM-Club...")
        nnm_results = _search_nnmclub(search_query)
        for r in nnm_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # Additional torrent sites (work in both modes)
    if ADDON.getSetting('torlock_enabled') != 'false':
        if progress:
            progress.update(85, "Searching Torlock...")
        tl_results = _search_torlock(search_query)
        for r in tl_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('glodls_enabled') != 'false':
        if progress:
            progress.update(86, "Searching GloDLS...")
        gl_results = _search_glodls(search_query)
        for r in gl_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('magnetdl_enabled') != 'false':
        if progress:
            progress.update(87, "Searching MagnetDL...")
        md_results = _search_magnetdl(search_query)
        for r in md_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    if ADDON.getSetting('kickass_enabled') != 'false':
        if progress:
            progress.update(88, "Searching KickAss...")
        ka_results = _search_kickass(search_query)
        for r in ka_results:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
            if hash_match:
                h = hash_match.group(1).upper()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    results.append(r)
    
    # TorrServer (local library search)
    if ADDON.getSetting('torrserver_url'):
        if progress:
            progress.update(89, "Searching TorrServer...")
        ts_results = _search_torrserver(search_query)
        for r in ts_results:
            results.append(r)
    
    # Get magnets for results that need them
    if progress:
        progress.update(90, "Fetching magnet links...")
    
    for r in results:
        if 'magnet' not in r and 'page_url' in r:
            magnet = _get_magnet_from_1337x(r['page_url'])
            if magnet:
                r['magnet'] = magnet
    
    results = [r for r in results if r.get('magnet')]
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
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
    
    sorted_sources = sorted(
        sources,
        key=lambda x: (
            quality_order.get(x.get('quality', 'Unknown'), 4),
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
    elif source_type == 'orionoid':
        return [s for s in sources if s.get('source_type') == 'orionoid']
    elif source_type == 'torrentio':
        return [s for s in sources if s.get('source_type') == 'torrentio']
    elif source_type == 'mediafusion':
        return [s for s in sources if s.get('source_type') == 'mediafusion']
    elif source_type == 'jackettio':
        return [s for s in sources if s.get('source_type') == 'jackettio']
    elif source_type == 'coco':
        return [s for s in sources if s.get('source_type') == 'coco']
    
    return sources
