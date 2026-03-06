# -*- coding: utf-8 -*-
"""
Torrent & Stream Scraper for Orion v2.5.0
Maximum source coverage with all working scrapers
"""

import urllib.request
import urllib.parse
import re
import ssl
import json
import xbmc
import xbmcaddon
import time

SSL_CONTEXT = ssl._create_unverified_context()
ADDON = xbmcaddon.Addon()

# Stremio Addon Base URLs
TORRENTIO_BASE = "https://torrentio.strem.fun"

# VidSrc domains
VIDSRC_DOMAINS = [
    "https://vidsrc.to",
    "https://vidsrc.pro",
    "https://vidsrc.cc",
    "https://vidsrc.me",
    "https://vidsrc.xyz",
    "https://vidsrc.in",
]

# Additional streaming embed sites
EMBED_SITES = [
    "https://2embed.cc",
    "https://www.2embed.cc",
    "https://multiembed.mov",
]

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
        xbmc.log(f"API error for {url[:80]}: {e}", xbmc.LOGWARNING)
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
    ]
    
    encoded_name = urllib.parse.quote(name)
    tracker_params = "&".join([f"tr={urllib.parse.quote(t)}" for t in trackers])
    
    return f"magnet:?xt=urn:btih:{info_hash}&dn={encoded_name}&{tracker_params}"

# ============== TORRENTIO ==============

def _search_torrentio(imdb_id, media_type='movie', season=None, episode=None):
    """Search Torrentio Stremio addon for streams"""
    results = []
    
    if not imdb_id:
        xbmc.log("Torrentio: No IMDB ID provided", xbmc.LOGWARNING)
        return results
    
    # Ensure IMDB ID is properly formatted
    if not imdb_id.startswith('tt'):
        imdb_id = f"tt{imdb_id}"
    
    try:
        if media_type == 'movie':
            url = f"{TORRENTIO_BASE}/stream/movie/{imdb_id}.json"
        else:
            url = f"{TORRENTIO_BASE}/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"Torrentio URL: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=30)
        
        if not data or 'streams' not in data:
            xbmc.log("Torrentio: No streams in response", xbmc.LOGINFO)
            return results
        
        for stream in data.get('streams', []):
            try:
                name = stream.get('name', '') or stream.get('title', 'Unknown')
                title = stream.get('title', '') or name
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    continue
                
                quality = _detect_quality(f"{name} {title}")
                
                # Parse size and seeds
                size = ''
                seeds = 0
                size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB))', title, re.IGNORECASE)
                if size_match:
                    size = size_match.group(1)
                seeds_match = re.search(r'(\d+)\s*(?:seeds?|👤)', title, re.IGNORECASE)
                if seeds_match:
                    seeds = int(seeds_match.group(1))
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': f"{name} - {title}" if title != name else name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Torrentio',
                    'source_type': 'torrentio',
                    'debrid': True
                })
            except Exception as e:
                xbmc.log(f"Torrentio parse error: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"Torrentio found {len(results)} streams", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Torrentio error: {e}", xbmc.LOGERROR)
    
    return results

# ============== YTS ==============

def _search_yts(query, year=''):
    """Search YTS API for movies"""
    results = []
    
    try:
        search_query = f"{query} {year}".strip() if year else query
        # Use alternative YTS domain
        urls_to_try = [
            f"https://yts.mx/api/v2/list_movies.json?query_term={urllib.parse.quote(search_query)}&limit=20",
            f"https://yts.torrentbay.st/api/v2/list_movies.json?query_term={urllib.parse.quote(search_query)}&limit=20",
        ]
        
        data = None
        for url in urls_to_try:
            data = _fetch_json(url, timeout=15)
            if data and data.get('status') == 'ok':
                break
        
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
    """Search 1337x for torrents - using mirror sites"""
    results = []
    
    # Try multiple mirrors
    mirrors = [
        "https://1337x.to",
        "https://1337x.st", 
        "https://1337x.ws",
        "https://x1337x.ws",
    ]
    
    for base_url in mirrors:
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"{base_url}/search/{encoded_query}/1/"
            
            html = _fetch_page(url, timeout=15)
            if not html or len(html) < 1000:
                continue
            
            # Parse search results - look for torrent links
            pattern = r'<a href="(/torrent/\d+/[^"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)
            
            for link, name in matches[:15]:
                name = name.strip()
                query_words = query.lower().split()[:2]
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
                    'page_url': f"{base_url}{link}"
                })
            
            if results:
                xbmc.log(f"1337x found {len(results)} results from {base_url}", xbmc.LOGINFO)
                break
                
        except Exception as e:
            xbmc.log(f"1337x error ({base_url}): {e}", xbmc.LOGWARNING)
            continue
    
    return results

def _get_magnet_from_1337x(page_url):
    """Get magnet link from 1337x torrent page"""
    try:
        html = _fetch_page(page_url, timeout=10)
        if html:
            match = re.search(r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)', html)
            if match:
                return match.group(1)
    except Exception as e:
        xbmc.log(f"1337x magnet error: {e}", xbmc.LOGWARNING)
    return None

# ============== PIRATEBAY ==============

def _search_piratebay(query):
    """Search Piratebay via API"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        # Use apibay.org API
        url = f"https://apibay.org/q.php?q={encoded_query}&cat=200,201,202,207,208,209"
        
        data = _fetch_json(url, timeout=15)
        
        if not data or not isinstance(data, list):
            return results
        
        for item in data[:20]:
            name = item.get('name', '')
            info_hash = item.get('info_hash', '')
            size_bytes = int(item.get('size', 0))
            seeders = int(item.get('seeders', 0))
            
            if not info_hash or info_hash == '0' or not name:
                continue
            
            # Skip low seeders
            if seeders < 1:
                continue
            
            # Format size
            if size_bytes > 1073741824:
                size = f"{size_bytes / 1073741824:.1f} GB"
            elif size_bytes > 1048576:
                size = f"{size_bytes / 1048576:.0f} MB"
            else:
                size = ''
            
            magnet = _create_magnet(info_hash, name)
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': size,
                'seeds': seeders,
                'source': 'PirateBay',
                'source_type': 'torrent',
                'debrid': True
            })
        
        xbmc.log(f"PirateBay found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"PirateBay error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== EZTV ==============

def _search_eztv(imdb_id, title=None, season=None, episode=None):
    """Search EZTV API for TV show torrents"""
    results = []
    
    try:
        # Try IMDB search first
        if imdb_id:
            clean_id = imdb_id.replace('tt', '')
            url = f"https://eztvx.to/api/get-torrents?imdb_id={clean_id}&limit=100"
        else:
            return results
        
        data = _fetch_json(url, timeout=15)
        
        if not data or 'torrents' not in data:
            return results
        
        for torrent in data.get('torrents', []):
            name = torrent.get('filename', torrent.get('title', 'Unknown'))
            info_hash = torrent.get('hash', '')
            size_bytes = torrent.get('size_bytes', 0)
            seeds = torrent.get('seeds', 0)
            
            # Filter by season/episode if specified
            if season and episode:
                name_lower = name.lower()
                ep_patterns = [
                    f's{int(season):02d}e{int(episode):02d}',
                    f'{season}x{int(episode):02d}',
                ]
                if not any(pat in name_lower for pat in ep_patterns):
                    continue
            
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

# ============== SOLIDTORRENTS ==============

def _search_solidtorrents(query):
    """Search SolidTorrents API"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://solidtorrents.to/api/v1/search?q={encoded_query}&category=Video&sort=seeders"
        
        data = _fetch_json(url, timeout=15)
        
        if not data or 'results' not in data:
            return results
        
        for item in data.get('results', [])[:25]:
            name = item.get('title', '')
            info_hash = item.get('infohash', '')
            size_bytes = item.get('size', 0)
            seeders = item.get('seeders', 0)
            
            if not info_hash or not name:
                continue
            
            if size_bytes > 1073741824:
                size = f"{size_bytes / 1073741824:.1f} GB"
            elif size_bytes > 1048576:
                size = f"{size_bytes / 1048576:.0f} MB"
            else:
                size = ''
            
            magnet = _create_magnet(info_hash, name)
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': size,
                'seeds': seeders,
                'source': 'SolidTorrents',
                'source_type': 'torrent',
                'debrid': True
            })
        
        xbmc.log(f"SolidTorrents found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"SolidTorrents error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== BTDIG ==============

def _search_btdig(query):
    """Search BTDig for torrents"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://btdig.com/search?q={encoded_query}&order=0"
        
        html = _fetch_page(url, timeout=15)
        if not html:
            return results
        
        # Parse magnet links
        pattern = r'(magnet:\?xt=urn:btih:[a-fA-F0-9]{40}[^"\'<>\s]*)'
        magnets = re.findall(pattern, html)
        
        # Also get names
        name_pattern = r'<div class="one_result">.*?<a[^>]+>([^<]+)</a>'
        names = re.findall(name_pattern, html, re.DOTALL)
        
        for i, magnet in enumerate(magnets[:20]):
            dn_match = re.search(r'dn=([^&]+)', magnet)
            name = urllib.parse.unquote_plus(dn_match.group(1)) if dn_match else (names[i] if i < len(names) else 'Unknown')
            
            results.append({
                'name': name,
                'magnet': magnet,
                'quality': _detect_quality(name),
                'size': '',
                'seeds': 0,
                'source': 'BTDig',
                'source_type': 'torrent',
                'debrid': True
            })
        
        xbmc.log(f"BTDig found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"BTDig error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== NYAA (Anime) ==============

def _search_nyaa(query):
    """Search Nyaa for anime torrents"""
    results = []
    
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://nyaa.si/?f=0&c=1_2&q={encoded_query}&s=seeders&o=desc"
        
        html = _fetch_page(url, timeout=15)
        if not html:
            return results
        
        # Find magnet links
        pattern = r'(magnet:\?xt=urn:btih:[a-fA-F0-9]{40}[^"\'<>\s]*)'
        magnets = re.findall(pattern, html)
        
        for magnet in magnets[:15]:
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
                'source_type': 'torrent',
                'debrid': True
            })
        
        xbmc.log(f"Nyaa found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Nyaa error: {e}", xbmc.LOGWARNING)
    
    return results

# ============== VIDSRC ==============

def _extract_vidsrc_stream(embed_url, timeout=15):
    """Extract actual stream URL from VidSrc embed"""
    try:
        html = _fetch_page(embed_url, timeout=timeout)
        if not html:
            return None
        
        # Look for m3u8 stream URLs
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
        
        # Try to find video source in scripts
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
    
    # Prefer IMDB ID
    content_id = imdb_id if imdb_id else tmdb_id
    if not content_id:
        return results
    
    for domain in VIDSRC_DOMAINS:
        try:
            if media_type == 'movie':
                embed_url = f"{domain}/embed/movie/{content_id}"
            else:
                embed_url = f"{domain}/embed/tv/{content_id}/{season}/{episode}"
            
            # Quick check if URL responds
            html = _fetch_page(embed_url, timeout=8)
            if not html or len(html) < 500:
                continue
            
            # VidSrc provides embeds - add as stream options
            for quality in ['1080p', '720p', 'SD']:
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
                    'embed': True
                })
            
            xbmc.log(f"VidSrc found streams at {domain}", xbmc.LOGINFO)
            break
                
        except Exception as e:
            xbmc.log(f"VidSrc error for {domain}: {e}", xbmc.LOGWARNING)
            continue
    
    return results

# ============== STREAMING SITES ==============

def _scrape_streaming_sites(imdb_id, tmdb_id, title, media_type, season=None, episode=None):
    """Scrape direct streaming sites"""
    results = []
    
    sites = [
        ('HydraHD', 'https://hydrahd.cc', '/watch/{imdb_id}'),
        ('FlickyStream', 'https://flickystream.com', '/embed/{imdb_id}'),
        ('Cineby', 'https://cineby.app', '/movie/{imdb_id}'),
        ('2embed', 'https://2embed.cc', '/embed/{imdb_id}'),
    ]
    
    for site_name, base_url, path_template in sites:
        try:
            if media_type == 'tv' and season and episode:
                path = path_template.replace('{imdb_id}', f"{imdb_id}/{season}/{episode}")
            else:
                path = path_template.replace('{imdb_id}', str(imdb_id or tmdb_id))
            
            full_url = f"{base_url}{path}"
            
            # Quick availability check
            html = _fetch_page(full_url, timeout=5)
            if html and len(html) > 500 and 'error' not in html.lower():
                results.append({
                    'name': f"{site_name} Stream",
                    'stream_url': full_url,
                    'quality': '720p',
                    'size': 'Stream',
                    'seeds': 0,
                    'source': site_name,
                    'source_type': 'direct',
                    'debrid': False,
                    'direct_stream': True,
                    'embed': True
                })
                xbmc.log(f"{site_name} available at {full_url}", xbmc.LOGINFO)
                
        except Exception as e:
            continue
    
    return results

# ============== SOURCE SETTINGS ==============

def _is_source_enabled(source_name):
    """Check if a source is enabled in settings"""
    setting_map = {
        'torrentio': 'enable_torrentio',
        'yts': 'enable_yts',
        'eztv': 'enable_eztv',
        '1337x': 'enable_1337x',
        'piratebay': 'enable_piratebay',
        'vidsrc': 'enable_vidsrc',
        'streaming_sites': 'enable_streaming_sites',
    }
    setting_id = setting_map.get(source_name.lower())
    if setting_id:
        val = ADDON.getSetting(setting_id)
        return val != 'false'
    return True

# ============== MAIN SEARCH FUNCTIONS ==============

def search_movie(title, year='', tmdb_id=None, progress=None):
    """Search for movie sources across all scrapers"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} {year}".strip() if year else title
    
    # Get IMDB ID from TMDB
    imdb_id = None
    if tmdb_id:
        try:
            from resources.lib import tmdb
            external_ids = tmdb.get_external_ids('movie', tmdb_id)
            if external_ids:
                imdb_id = external_ids.get('imdb_id')
                xbmc.log(f"Got IMDB ID: {imdb_id} for TMDB: {tmdb_id}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Could not get IMDB ID: {e}", xbmc.LOGWARNING)
    
    def add_results(new_results):
        """Add results avoiding duplicates"""
        for r in new_results:
            if 'magnet' in r:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
            results.append(r)
    
    # 1. Torrentio (best source)
    if _is_source_enabled('torrentio') and imdb_id:
        if progress:
            progress.update(3, "Searching Torrentio...")
        add_results(_search_torrentio(imdb_id, 'movie'))
    
    # 2. YTS (great for movies)
    if _is_source_enabled('yts'):
        if progress:
            progress.update(10, "Searching YTS...")
        add_results(_search_yts(title, year))
    
    # 3. PirateBay API
    if _is_source_enabled('piratebay'):
        if progress:
            progress.update(20, "Searching PirateBay...")
        add_results(_search_piratebay(search_query))
    
    # 4. SolidTorrents
    if progress:
        progress.update(30, "Searching SolidTorrents...")
    add_results(_search_solidtorrents(search_query))
    
    # 5. BTDig
    if progress:
        progress.update(40, "Searching BTDig...")
    add_results(_search_btdig(search_query))
    
    # 6. 1337x
    if _is_source_enabled('1337x'):
        if progress:
            progress.update(50, "Searching 1337x...")
        results_1337x = _search_1337x(search_query)
        # Get magnets for 1337x results
        for r in results_1337x:
            if 'page_url' in r:
                magnet = _get_magnet_from_1337x(r['page_url'])
                if magnet:
                    r['magnet'] = magnet
                    add_results([r])
    
    # 5. VidSrc direct streams
    if _is_source_enabled('vidsrc'):
        if progress:
            progress.update(70, "Getting VidSrc streams...")
        if tmdb_id or imdb_id:
            results.extend(_get_vidsrc_streams(tmdb_id, 'movie', imdb_id=imdb_id))
    
    # 6. Other streaming sites
    if _is_source_enabled('streaming_sites'):
        if progress:
            progress.update(85, "Checking streaming sites...")
        results.extend(_scrape_streaming_sites(imdb_id, tmdb_id, title, 'movie'))
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
    xbmc.log(f"Total movie sources found: {len(results)}", xbmc.LOGINFO)
    return results

def search_episode(title, season, episode, tmdb_id=None, progress=None):
    """Search for TV episode sources"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} S{int(season):02d}E{int(episode):02d}"
    
    # Get IMDB ID
    imdb_id = None
    if tmdb_id:
        try:
            from resources.lib import tmdb
            external_ids = tmdb.get_external_ids('tv', tmdb_id)
            if external_ids:
                imdb_id = external_ids.get('imdb_id')
                xbmc.log(f"Got TV IMDB ID: {imdb_id}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Could not get IMDB ID: {e}", xbmc.LOGWARNING)
    
    def add_results(new_results):
        for r in new_results:
            if 'magnet' in r:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
            results.append(r)
    
    # 1. Torrentio
    if _is_source_enabled('torrentio') and imdb_id:
        if progress:
            progress.update(3, "Searching Torrentio...")
        add_results(_search_torrentio(imdb_id, 'tv', season, episode))
    
    # 2. EZTV (specialized for TV)
    if _is_source_enabled('eztv') and imdb_id:
        if progress:
            progress.update(15, "Searching EZTV...")
        add_results(_search_eztv(imdb_id, title, season, episode))
    
    # 3. PirateBay
    if _is_source_enabled('piratebay'):
        if progress:
            progress.update(25, "Searching PirateBay...")
        add_results(_search_piratebay(search_query))
    
    # 4. SolidTorrents
    if progress:
        progress.update(35, "Searching SolidTorrents...")
    add_results(_search_solidtorrents(search_query))
    
    # 5. BTDig
    if progress:
        progress.update(45, "Searching BTDig...")
    add_results(_search_btdig(search_query))
    
    # 6. Nyaa (for anime)
    if progress:
        progress.update(55, "Searching Nyaa...")
    add_results(_search_nyaa(search_query))
    
    # 7. 1337x
    if _is_source_enabled('1337x'):
        if progress:
            progress.update(65, "Searching 1337x...")
        results_1337x = _search_1337x(search_query)
        for r in results_1337x:
            if 'page_url' in r:
                magnet = _get_magnet_from_1337x(r['page_url'])
                if magnet:
                    r['magnet'] = magnet
                    add_results([r])
    
    # 8. VidSrc
    if _is_source_enabled('vidsrc'):
        if progress:
            progress.update(80, "Getting VidSrc streams...")
        if tmdb_id or imdb_id:
            results.extend(_get_vidsrc_streams(tmdb_id, 'tv', season, episode, imdb_id))
    
    # 9. Streaming sites
    if _is_source_enabled('streaming_sites'):
        if progress:
            progress.update(92, "Checking streaming sites...")
        results.extend(_scrape_streaming_sites(imdb_id, tmdb_id, title, 'tv', season, episode))
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
    xbmc.log(f"Total episode sources found: {len(results)}", xbmc.LOGINFO)
    return results

def sort_sources(sources, quality_filter=None):
    """Sort sources by quality and type"""
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
    
    source_type_order = {'torrentio': 0, 'torrent': 1, 'vidsrc': 2, 'direct': 3}
    
    return sorted(
        sources,
        key=lambda x: (
            quality_order.get(x.get('quality', 'Unknown'), 4),
            source_type_order.get(x.get('source_type', 'torrent'), 2),
            -x.get('seeds', 0)
        )
    )

def filter_sources_by_type(sources, source_type=None):
    """Filter sources by type"""
    if not source_type or source_type == 'all':
        return sources
    
    if source_type == 'debrid':
        return [s for s in sources if s.get('debrid')]
    elif source_type == 'torrentio':
        return [s for s in sources if s.get('source_type') == 'torrentio']
    elif source_type == 'torrent':
        return [s for s in sources if s.get('source_type') == 'torrent']
    elif source_type == 'vidsrc':
        return [s for s in sources if s.get('source_type') == 'vidsrc']
    elif source_type == 'direct':
        return [s for s in sources if s.get('source_type') in ['direct', 'vidsrc']]
    
    return sources
