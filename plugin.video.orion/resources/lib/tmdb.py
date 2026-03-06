# -*- coding: utf-8 -*-
"""
TMDB API Integration for Orion
"""

import urllib.request
import urllib.parse
import json
import ssl

TMDB_API_KEY = "f15af109700aab95d564acda15bdcd97"
BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE_URL = "https://image.tmdb.org/t/p"
SSL_CONTEXT = ssl._create_unverified_context()

def fetch_json(endpoint, params=None):
    """Fetch JSON from TMDB API"""
    url = f"{BASE_URL}{endpoint}"
    
    # Build query parameters
    query_params = {'api_key': TMDB_API_KEY}
    if params:
        query_params.update(params)
    
    url += "?" + urllib.parse.urlencode(query_params)
    
    headers = {'User-Agent': 'Orion/2.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"TMDB API Error: {e}")
        return {"results": [], "total_pages": 1}

def get_poster_url(path, size='w500'):
    """Get full poster URL"""
    if path:
        return f"{IMG_BASE_URL}/{size}{path}"
    return None

def get_backdrop_url(path, size='w1280'):
    """Get full backdrop URL"""
    if path:
        return f"{IMG_BASE_URL}/{size}{path}"
    return None

def get_genres(media_type):
    """Get list of genres for movies or TV"""
    data = fetch_json(f"/genre/{media_type}/list")
    return data.get('genres', [])

def get_category(media_type, category, page=1):
    """Get content by category"""
    endpoint = f"/{media_type}/{category}"
    return fetch_json(endpoint, {'page': page})

def get_by_genre(media_type, genre_id, page=1):
    """Get content by genre"""
    return fetch_json(f"/discover/{media_type}", {
        'with_genres': genre_id,
        'page': page,
        'sort_by': 'popularity.desc'
    })

def search_content(media_type, query, page=1):
    """Search movies or TV shows"""
    return fetch_json(f"/search/{media_type}", {
        'query': query,
        'page': page
    })

def search_people(query):
    """Search for people/actors"""
    return fetch_json("/search/person", {'query': query})

def get_person_credits(person_id, media_type='movie'):
    """Get person's filmography"""
    data = fetch_json(f"/person/{person_id}/combined_credits")
    
    # Filter by media type
    if media_type == 'movie':
        results = [item for item in data.get('cast', []) if item.get('media_type') == 'movie']
    else:
        results = [item for item in data.get('cast', []) if item.get('media_type') == 'tv']
    
    # Sort by popularity
    results.sort(key=lambda x: x.get('popularity', 0), reverse=True)
    
    return {'results': results[:50], 'total_pages': 1}

def get_movie_details(movie_id):
    """Get movie details"""
    return fetch_json(f"/movie/{movie_id}")

def get_tv_details(show_id):
    """Get TV show details including seasons"""
    return fetch_json(f"/tv/{show_id}")

def get_season_episodes(show_id, season_number):
    """Get episodes for a season"""
    return fetch_json(f"/tv/{show_id}/season/{season_number}")

def get_external_ids(media_type, item_id):
    """Get external IDs (IMDB, etc.)"""
    return fetch_json(f"/{media_type}/{item_id}/external_ids")

def get_watch_providers(media_type, region='US'):
    """Get list of available watch providers (streaming services)"""
    return fetch_json(f"/watch/providers/{media_type}", {'watch_region': region})

def get_provider_logo_url(path, size='w92'):
    """Get provider logo URL"""
    if path:
        return f"{IMG_BASE_URL}/{size}{path}"
    return None

def get_by_provider(media_type, provider_id, page=1, region='US'):
    """Get content by streaming provider"""
    return fetch_json(f"/discover/{media_type}", {
        'with_watch_providers': provider_id,
        'watch_region': region,
        'page': page,
        'sort_by': 'popularity.desc'
    })

def get_provider_details(media_type, item_id):
    """Get watch providers for a specific movie/show"""
    return fetch_json(f"/{media_type}/{item_id}/watch/providers")

# Popular streaming providers with their TMDB IDs and colors
STREAMING_PROVIDERS = {
    8: {'name': 'Netflix', 'color': 'red'},
    9: {'name': 'Amazon Prime Video', 'color': 'cyan'},
    337: {'name': 'Disney+', 'color': 'blue'},
    15: {'name': 'Hulu', 'color': 'lime'},
    1899: {'name': 'Max', 'color': 'purple'},  # HBO Max renamed to Max
    387: {'name': 'Peacock', 'color': 'yellow'},
    531: {'name': 'Paramount+', 'color': 'dodgerblue'},
    350: {'name': 'Apple TV+', 'color': 'gray'},
    283: {'name': 'Crunchyroll', 'color': 'orange'},
    386: {'name': 'Peacock Premium', 'color': 'yellow'},
    2: {'name': 'Apple iTunes', 'color': 'pink'},
    3: {'name': 'Google Play Movies', 'color': 'lime'},
    10: {'name': 'Amazon Video', 'color': 'orange'},
    192: {'name': 'YouTube', 'color': 'red'},
    188: {'name': 'YouTube Premium', 'color': 'red'},
    307: {'name': 'Showtime', 'color': 'red'},
    37: {'name': 'Showtime Amazon Channel', 'color': 'red'},
    43: {'name': 'Starz', 'color': 'gold'},
    230: {'name': 'Starz Play Amazon Channel', 'color': 'gold'},
    73: {'name': 'Tubi TV', 'color': 'orange'},
    300: {'name': 'Pluto TV', 'color': 'yellow'},
    257: {'name': 'fuboTV', 'color': 'orange'},
    393: {'name': 'Freevee', 'color': 'lime'},
    207: {'name': 'The Roku Channel', 'color': 'purple'},
    613: {'name': 'BritBox', 'color': 'red'},
    191: {'name': 'Kanopy', 'color': 'yellow'},
    546: {'name': 'AMC+', 'color': 'red'},
    526: {'name': 'AMC', 'color': 'red'},
    1770: {'name': 'Plex', 'color': 'orange'},
    538: {'name': 'Plex Channel', 'color': 'orange'},
    582: {'name': 'Bet+', 'color': 'purple'},
}