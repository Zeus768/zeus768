# -*- coding: utf-8 -*-
"""
Orion Media Explorer - Kodi 21 Omega Addon
Scrapes torrentdownloads.pro with multi-debrid and Trakt support
"""

import sys
import urllib.parse
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

# Addon info
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_FANART = ADDON.getAddonInfo('fanart')

BASE_URL = sys.argv[0]
HANDLE = int(sys.argv[1])

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

def build_url(query):
    return f"{BASE_URL}?{urllib.parse.urlencode(query)}"

def add_directory_item(name, query, is_folder=True, icon=None, fanart=None, plot=""):
    """Add a directory item with artwork"""
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        'icon': icon or ADDON_ICON,
        'thumb': icon or ADDON_ICON,
        'poster': icon or ADDON_ICON,
        'fanart': fanart or ADDON_FANART
    })
    li.setInfo('video', {'title': name, 'plot': plot})
    xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, isFolder=is_folder)

def main_menu():
    """Display main menu"""
    items = [
        ("[B]Movies[/B]", {'action': 'movies_menu'}, True, "Browse movies by genre"),
        ("[B]TV Shows[/B]", {'action': 'tvshows_menu'}, True, "Browse TV shows by genre"),
        ("[B]In Cinema[/B]", {'action': 'in_cinema'}, True, "Currently showing in theaters"),
        ("[B]Latest Episodes[/B]", {'action': 'latest_episodes'}, True, "Latest TV show episodes"),
        ("[B]Search[/B]", {'action': 'search_menu'}, True, "Search movies, TV shows, actors"),
        ("[COLOR yellow]Trakt[/COLOR]", {'action': 'trakt_menu'}, True, "Trakt lists and watchlist"),
        ("[COLOR cyan]Settings[/COLOR]", {'action': 'open_settings'}, False, "Configure addon settings"),
    ]
    
    for name, query, is_folder, plot in items:
        add_directory_item(name, query, is_folder, plot=plot)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def movies_menu():
    """Movies sub-menu with genres"""
    from resources.lib import tmdb
    
    # Add special categories
    add_directory_item("[B]Popular Movies[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'popular', 'page': 1})
    add_directory_item("[B]Top Rated Movies[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'top_rated', 'page': 1})
    add_directory_item("[B]Now Playing[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'now_playing', 'page': 1})
    add_directory_item("[B]Upcoming[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'upcoming', 'page': 1})
    
    # Add streaming providers section
    add_directory_item("[COLOR magenta][B]Browse by Streaming Service[/B][/COLOR]", {'action': 'providers_menu', 'type': 'movie'})
    
    # Add genres
    genres = tmdb.get_genres('movie')
    for genre in genres:
        add_directory_item(
            f"[COLOR lime]{genre['name']}[/COLOR]",
            {'action': 'list_content', 'type': 'movie', 'genre': genre['id'], 'page': 1}
        )
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def tvshows_menu():
    """TV Shows sub-menu with genres"""
    from resources.lib import tmdb
    
    # Add special categories
    add_directory_item("[B]Popular TV Shows[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'popular', 'page': 1})
    add_directory_item("[B]Top Rated TV Shows[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'top_rated', 'page': 1})
    add_directory_item("[B]On The Air[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'on_the_air', 'page': 1})
    add_directory_item("[B]Airing Today[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'airing_today', 'page': 1})
    
    # Add streaming providers section
    add_directory_item("[COLOR magenta][B]Browse by Streaming Service[/B][/COLOR]", {'action': 'providers_menu', 'type': 'tv'})
    
    # Add genres
    genres = tmdb.get_genres('tv')
    for genre in genres:
        add_directory_item(
            f"[COLOR lime]{genre['name']}[/COLOR]",
            {'action': 'list_content', 'type': 'tv', 'genre': genre['id'], 'page': 1}
        )
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def providers_menu(params):
    """Show streaming providers menu with icons"""
    from resources.lib import tmdb
    
    media_type = params.get('type', 'movie')
    
    # Get region from settings (labelenum returns index)
    region_codes = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'ES', 'IT', 'JP', 'KR', 'BR', 'MX', 'IN']
    region_idx = ADDON.getSetting('provider_region')
    try:
        region = region_codes[int(region_idx)] if region_idx else 'US'
    except (ValueError, IndexError):
        region = 'US'
    
    # Get available providers from TMDB
    providers_data = tmdb.get_watch_providers(media_type, region)
    available_providers = providers_data.get('results', [])
    
    # Create a lookup dict for available providers
    available_ids = {p['provider_id']: p for p in available_providers}
    
    # Define major providers with custom colors (shown first)
    major_providers = [
        (8, 'Netflix', 'red'),
        (337, 'Disney+', 'dodgerblue'),
        (9, 'Amazon Prime Video', 'cyan'),
        (1899, 'Max (HBO)', 'purple'),
        (15, 'Hulu', 'lime'),
        (531, 'Paramount+', 'blue'),
        (350, 'Apple TV+', 'silver'),
        (387, 'Peacock', 'yellow'),
        (283, 'Crunchyroll', 'orange'),
        (73, 'Tubi TV', 'orange'),
        (300, 'Pluto TV', 'yellow'),
        (207, 'Roku Channel', 'purple'),
        (386, 'Peacock Premium', 'yellow'),
        (43, 'Starz', 'gold'),
        (307, 'Showtime', 'red'),
        (546, 'AMC+', 'red'),
        (191, 'Kanopy', 'yellow'),
        (257, 'fuboTV', 'orange'),
        (393, 'Freevee', 'lime'),
        (613, 'BritBox', 'red'),
        (1770, 'Plex', 'orange'),
    ]
    
    # Show major providers first
    shown_ids = set()
    for provider_id, name, color in major_providers:
        if provider_id in available_ids:
            provider = available_ids[provider_id]
            shown_ids.add(provider_id)
            
            logo = tmdb.get_provider_logo_url(provider.get('logo_path'), 'w154')
            
            display_name = f"[COLOR {color}][B]{name}[/B][/COLOR]"
            
            li = xbmcgui.ListItem(label=display_name)
            li.setArt({
                'icon': logo or ADDON_ICON,
                'thumb': logo or ADDON_ICON,
                'poster': logo or ADDON_ICON,
                'fanart': ADDON_FANART
            })
            
            url = build_url({
                'action': 'list_by_provider',
                'type': media_type,
                'provider_id': provider_id,
                'provider_name': name,
                'page': 1
            })
            
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Add separator for other providers
    if len(available_providers) > len(shown_ids):
        li = xbmcgui.ListItem(label="[COLOR gray]─── Other Services ───[/COLOR]")
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    # Show remaining providers
    for provider in sorted(available_providers, key=lambda x: x.get('display_priority', 999)):
        provider_id = provider.get('provider_id')
        if provider_id in shown_ids:
            continue
        
        name = provider.get('provider_name', 'Unknown')
        logo = tmdb.get_provider_logo_url(provider.get('logo_path'), 'w154')
        
        li = xbmcgui.ListItem(label=f"[COLOR white]{name}[/COLOR]")
        li.setArt({
            'icon': logo or ADDON_ICON,
            'thumb': logo or ADDON_ICON,
            'poster': logo or ADDON_ICON,
            'fanart': ADDON_FANART
        })
        
        url = build_url({
            'action': 'list_by_provider',
            'type': media_type,
            'provider_id': provider_id,
            'provider_name': name,
            'page': 1
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE)

def list_by_provider(params):
    """List content by streaming provider"""
    from resources.lib import tmdb
    
    media_type = params.get('type', 'movie')
    provider_id = params.get('provider_id')
    provider_name = params.get('provider_name', 'Unknown')
    page = int(params.get('page', 1))
    
    # Get region from settings
    region_codes = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'ES', 'IT', 'JP', 'KR', 'BR', 'MX', 'IN']
    region_idx = ADDON.getSetting('provider_region')
    try:
        region = region_codes[int(region_idx)] if region_idx else 'US'
    except (ValueError, IndexError):
        region = 'US'
    
    log(f"Listing {media_type} from provider {provider_name} (ID: {provider_id})")
    
    data = tmdb.get_by_provider(media_type, provider_id, page, region)
    
    results = data.get('results', [])
    total_pages = data.get('total_pages', 1)
    
    if not results:
        xbmcgui.Dialog().notification('Orion', f'No content found on {provider_name}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    for item in results:
        title = item.get('title') or item.get('name', 'Unknown')
        item_id = item.get('id')
        poster = tmdb.get_poster_url(item.get('poster_path'))
        backdrop = tmdb.get_backdrop_url(item.get('backdrop_path'))
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        rating = item.get('vote_average', 0)
        plot = item.get('overview', '')
        
        display_title = f"{title} ({year})" if year else title
        if rating:
            display_title = f"{display_title} [COLOR yellow]★{rating:.1f}[/COLOR]"
        
        li = xbmcgui.ListItem(label=display_title)
        li.setArt({
            'icon': poster,
            'thumb': poster,
            'poster': poster,
            'fanart': backdrop or ADDON_FANART
        })
        
        info = {
            'title': title,
            'plot': plot,
            'year': int(year) if year else None,
            'rating': rating,
            'mediatype': 'movie' if media_type == 'movie' else 'tvshow'
        }
        li.setInfo('video', info)
        
        action = 'movie_sources' if media_type == 'movie' else 'tv_seasons'
        url = build_url({'action': action, 'id': item_id, 'title': title, 'year': year})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Pagination
    if page < total_pages and page < 50:  # Limit to 50 pages
        next_params = dict(params)
        next_params['page'] = page + 1
        add_directory_item(f"[B]Next Page ({page+1}/{min(total_pages, 50)})[/B]", next_params)
    
    content_type = 'movies' if media_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(HANDLE, content_type)
    xbmcplugin.endOfDirectory(HANDLE)

def list_content(params):
    """List movies or TV shows"""
    from resources.lib import tmdb
    
    media_type = params.get('type', 'movie')
    page = int(params.get('page', 1))
    genre = params.get('genre')
    category = params.get('category')
    query = params.get('query')
    person_id = params.get('person_id')
    
    if query:
        data = tmdb.search_content(media_type, query, page)
    elif person_id:
        data = tmdb.get_person_credits(person_id, media_type)
    elif category:
        data = tmdb.get_category(media_type, category, page)
    elif genre:
        data = tmdb.get_by_genre(media_type, genre, page)
    else:
        data = tmdb.get_category(media_type, 'popular', page)
    
    results = data.get('results', data.get('cast', []))
    total_pages = data.get('total_pages', 1)
    
    for item in results:
        title = item.get('title') or item.get('name', 'Unknown')
        item_id = item.get('id')
        poster = tmdb.get_poster_url(item.get('poster_path'))
        backdrop = tmdb.get_backdrop_url(item.get('backdrop_path'))
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        rating = item.get('vote_average', 0)
        plot = item.get('overview', '')
        
        display_title = f"{title} ({year})" if year else title
        if rating:
            display_title = f"{display_title} [COLOR yellow]★{rating:.1f}[/COLOR]"
        
        li = xbmcgui.ListItem(label=display_title)
        li.setArt({
            'icon': poster,
            'thumb': poster,
            'poster': poster,
            'fanart': backdrop or ADDON_FANART
        })
        
        info = {
            'title': title,
            'plot': plot,
            'year': int(year) if year else None,
            'rating': rating,
            'mediatype': 'movie' if media_type == 'movie' else 'tvshow'
        }
        li.setInfo('video', info)
        
        action = 'movie_sources' if media_type == 'movie' else 'tv_seasons'
        url = build_url({'action': action, 'id': item_id, 'title': title, 'year': year})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Pagination
    if page < total_pages:
        next_params = dict(params)
        next_params['page'] = page + 1
        add_directory_item(f"[B]Next Page ({page+1}/{total_pages})[/B]", next_params)
    
    content_type = 'movies' if media_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(HANDLE, content_type)
    xbmcplugin.endOfDirectory(HANDLE)

def tv_seasons(params):
    """List TV show seasons"""
    from resources.lib import tmdb
    
    show_id = params.get('id')
    show_title = params.get('title', '')
    
    details = tmdb.get_tv_details(show_id)
    seasons = details.get('seasons', [])
    
    for season in seasons:
        season_num = season.get('season_number', 0)
        name = season.get('name', f'Season {season_num}')
        episode_count = season.get('episode_count', 0)
        poster = tmdb.get_poster_url(season.get('poster_path'))
        
        display_name = f"{name} ({episode_count} episodes)"
        
        li = xbmcgui.ListItem(label=display_name)
        li.setArt({
            'icon': poster or ADDON_ICON,
            'thumb': poster or ADDON_ICON,
            'poster': poster or ADDON_ICON,
            'fanart': ADDON_FANART
        })
        
        url = build_url({
            'action': 'tv_episodes',
            'id': show_id,
            'title': show_title,
            'season': season_num
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)

def tv_episodes(params):
    """List TV show episodes"""
    from resources.lib import tmdb
    
    show_id = params.get('id')
    show_title = params.get('title', '')
    season_num = int(params.get('season', 1))
    
    episodes = tmdb.get_season_episodes(show_id, season_num)
    
    for ep in episodes.get('episodes', []):
        ep_num = ep.get('episode_number', 0)
        ep_name = ep.get('name', f'Episode {ep_num}')
        still = tmdb.get_backdrop_url(ep.get('still_path'))
        plot = ep.get('overview', '')
        air_date = ep.get('air_date', '')
        rating = ep.get('vote_average', 0)
        
        display_name = f"S{season_num:02d}E{ep_num:02d} - {ep_name}"
        if rating:
            display_name = f"{display_name} [COLOR yellow]★{rating:.1f}[/COLOR]"
        
        li = xbmcgui.ListItem(label=display_name)
        li.setArt({
            'icon': still or ADDON_ICON,
            'thumb': still or ADDON_ICON,
            'fanart': still or ADDON_FANART
        })
        li.setInfo('video', {
            'title': ep_name,
            'plot': plot,
            'episode': ep_num,
            'season': season_num,
            'aired': air_date,
            'mediatype': 'episode'
        })
        
        url = build_url({
            'action': 'episode_sources',
            'title': show_title,
            'season': season_num,
            'episode': ep_num
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)

def search_menu():
    """Search sub-menu"""
    items = [
        ("[B]Search Movies[/B]", {'action': 'search', 'type': 'movie'}),
        ("[B]Search TV Shows[/B]", {'action': 'search', 'type': 'tv'}),
        ("[B]Search by Actor[/B]", {'action': 'search_actor'}),
    ]
    
    for name, query in items:
        add_directory_item(name, query)
    
    xbmcplugin.endOfDirectory(HANDLE)

def do_search(params):
    """Perform search"""
    media_type = params.get('type', 'movie')
    
    keyboard = xbmc.Keyboard('', f'Search {media_type.title()}s')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText().strip()
        if query:
            list_content({'type': media_type, 'query': query, 'page': 1})
            return
    
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def search_actor(params):
    """Search for actor"""
    from resources.lib import tmdb
    
    keyboard = xbmc.Keyboard('', 'Search Actor')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText().strip()
        if query:
            results = tmdb.search_people(query)
            
            for person in results.get('results', []):
                name = person.get('name', 'Unknown')
                person_id = person.get('id')
                profile = tmdb.get_poster_url(person.get('profile_path'))
                known_for = person.get('known_for_department', '')
                
                li = xbmcgui.ListItem(label=f"{name} ({known_for})")
                li.setArt({
                    'icon': profile or ADDON_ICON,
                    'thumb': profile or ADDON_ICON,
                    'fanart': ADDON_FANART
                })
                
                url = build_url({'action': 'actor_works', 'id': person_id, 'name': name})
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            
            xbmcplugin.endOfDirectory(HANDLE)
            return
    
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def actor_works(params):
    """Show actor's filmography"""
    person_id = params.get('id')
    actor_name = params.get('name', '')
    
    add_directory_item(f"[B]{actor_name}'s Movies[/B]", {'action': 'list_content', 'type': 'movie', 'person_id': person_id})
    add_directory_item(f"[B]{actor_name}'s TV Shows[/B]", {'action': 'list_content', 'type': 'tv', 'person_id': person_id})
    
    xbmcplugin.endOfDirectory(HANDLE)

def in_cinema(params):
    """Movies currently in cinema"""
    list_content({'type': 'movie', 'category': 'now_playing', 'page': params.get('page', 1)})

def latest_episodes(params):
    """Latest TV episodes"""
    list_content({'type': 'tv', 'category': 'on_the_air', 'page': params.get('page', 1)})

def movie_sources(params):
    """Get movie sources from scraper"""
    from resources.lib import scraper
    
    title = params.get('title', '')
    year = params.get('year', '')
    tmdb_id = params.get('id', '')
    quality_filter = params.get('quality_filter', 'all')
    source_filter = params.get('source_filter', 'all')
    
    progress = xbmcgui.DialogProgress()
    progress.create('Orion', f'Searching sources for {title}...')
    
    try:
        sources = scraper.search_movie(title, year, tmdb_id, progress)
        progress.close()
        
        if not sources:
            xbmcgui.Dialog().notification('Orion', 'No sources found', ADDON_ICON)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        
        # Apply filters
        sources = scraper.filter_sources_by_type(sources, source_filter)
        sources = scraper.sort_sources(sources, quality_filter)
        
        show_sources(sources, title, tmdb_id, 'movie', params)
    except Exception as e:
        progress.close()
        log(f"Error getting sources: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Orion', f'Error: {str(e)}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def episode_sources(params):
    """Get episode sources from scraper"""
    from resources.lib import scraper
    
    title = params.get('title', '')
    season = int(params.get('season', 1))
    episode = int(params.get('episode', 1))
    tmdb_id = params.get('id', '')
    quality_filter = params.get('quality_filter', 'all')
    source_filter = params.get('source_filter', 'all')
    
    progress = xbmcgui.DialogProgress()
    progress.create('Orion', f'Searching sources for {title} S{season}E{episode}...')
    
    try:
        sources = scraper.search_episode(title, season, episode, tmdb_id, progress)
        progress.close()
        
        if not sources:
            xbmcgui.Dialog().notification('Orion', 'No sources found', ADDON_ICON)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        
        # Apply filters
        sources = scraper.filter_sources_by_type(sources, source_filter)
        sources = scraper.sort_sources(sources, quality_filter)
        
        show_sources(sources, f"{title} S{season:02d}E{episode:02d}", tmdb_id, 'tv', params)
    except Exception as e:
        progress.close()
        log(f"Error getting sources: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Orion', f'Error: {str(e)}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def show_sources(sources, title, tmdb_id=None, media_type='movie', original_params=None):
    """Display available sources with color coding and filtering options"""
    from resources.lib import scraper
    
    # Add filter options at the top
    current_quality = (original_params or {}).get('quality_filter', 'all')
    current_source = (original_params or {}).get('source_filter', 'all')
    
    # Quality filter menu item
    quality_label = f"[COLOR magenta]Filter Quality: {current_quality.upper()}[/COLOR]"
    li = xbmcgui.ListItem(label=quality_label)
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({
        'action': 'filter_quality',
        'title': (original_params or {}).get('title', title),
        'year': (original_params or {}).get('year', ''),
        'id': tmdb_id or '',
        'media_type': media_type,
        'season': (original_params or {}).get('season', ''),
        'episode': (original_params or {}).get('episode', ''),
        'current_source_filter': current_source
    })
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Source filter menu item
    source_label = f"[COLOR magenta]Filter Source: {current_source.upper()}[/COLOR]"
    li = xbmcgui.ListItem(label=source_label)
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({
        'action': 'filter_source',
        'title': (original_params or {}).get('title', title),
        'year': (original_params or {}).get('year', ''),
        'id': tmdb_id or '',
        'media_type': media_type,
        'season': (original_params or {}).get('season', ''),
        'episode': (original_params or {}).get('episode', ''),
        'current_quality_filter': current_quality
    })
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Sort sources by quality
    quality_order = {'4K': 0, '2160p': 0, '1080p': 1, '720p': 2, 'SD': 3, '480p': 3, 'Unknown': 4}
    sources.sort(key=lambda x: (quality_order.get(x.get('quality', 'Unknown'), 4), -x.get('seeds', 0)))
    
    for source in sources:
        quality = source.get('quality', 'Unknown')
        size = source.get('size', '')
        seeds = source.get('seeds', 0)
        name = source.get('name', 'Unknown')
        source_type = source.get('source_type', 'torrent')
        source_name = source.get('source', 'Unknown')
        is_direct = source.get('direct_stream', False)
        is_ddl = source.get('ddl_link', False)
        
        # Source color coding:
        # Magenta = Torrentio (Stremio addon)
        # Purple = MediaFusion (Stremio addon)
        # Blue = Orionoid
        # Yellow = normal torrent scrapers with debrid
        # Red = VidSrc (direct stream)
        # Orange = Other streaming sites
        # Gray = DDL links
        if source_type == 'torrentio':
            source_tag = '[COLOR magenta][Torrentio][/COLOR]'
        elif source_type == 'mediafusion':
            source_tag = '[COLOR orchid][MediaFusion][/COLOR]'
        elif source_type == 'orionoid':
            source_tag = '[COLOR dodgerblue][Orionoid][/COLOR]'
        elif source_type == 'vidsrc':
            source_tag = '[COLOR red][VidSrc][/COLOR]'
        elif source_type == 'direct':
            source_tag = f'[COLOR orange][{source_name}][/COLOR]'
        elif source_type == 'ddl':
            source_tag = f'[COLOR gray][{source_name}][/COLOR]'
        else:  # torrent
            source_tag = f'[COLOR yellow][{source_name}][/COLOR]'
        
        # Quality color coding
        if quality in ['4K', '2160p']:
            quality_color = 'gold'
        elif quality == '1080p':
            quality_color = 'lime'
        elif quality == '720p':
            quality_color = 'cyan'
        else:
            quality_color = 'white'
        
        # Build display string
        display = f"{source_tag} [COLOR {quality_color}][{quality}][/COLOR] {name[:60]}"
        if size:
            display += f" [{size}]"
        if seeds and not is_direct:
            display += f" [COLOR lime]S:{seeds}[/COLOR]"
        if is_direct:
            display += " [COLOR red][DIRECT][/COLOR]"
        if is_ddl:
            display += " [COLOR gray][DDL][/COLOR]"
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        li.setProperty('IsPlayable', 'true')
        
        if is_direct or is_ddl:
            # Direct stream or DDL link
            url = build_url({
                'action': 'play_direct',
                'stream_url': source.get('stream_url', ''),
                'title': title,
                'quality': quality
            })
        else:
            # Debrid torrent
            url = build_url({
                'action': 'play',
                'magnet': source.get('magnet', ''),
                'title': title,
                'quality': quality
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def filter_quality(params):
    """Show quality filter options"""
    title = params.get('title', '')
    year = params.get('year', '')
    tmdb_id = params.get('id', '')
    media_type = params.get('media_type', 'movie')
    season = params.get('season', '')
    episode = params.get('episode', '')
    current_source = params.get('current_source_filter', 'all')
    
    options = [
        ('All Qualities', 'all'),
        ('4K Only', '4k'),
        ('1080p Only', '1080p'),
        ('720p Only', '720p'),
        ('SD Only', 'sd'),
    ]
    
    for label, quality_value in options:
        li = xbmcgui.ListItem(label=f"[COLOR cyan]{label}[/COLOR]")
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        if media_type == 'tv' and season and episode:
            url = build_url({
                'action': 'episode_sources',
                'title': title,
                'id': tmdb_id,
                'season': season,
                'episode': episode,
                'quality_filter': quality_value,
                'source_filter': current_source
            })
        else:
            url = build_url({
                'action': 'movie_sources',
                'title': title,
                'year': year,
                'id': tmdb_id,
                'quality_filter': quality_value,
                'source_filter': current_source
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def filter_source(params):
    """Show source filter options"""
    title = params.get('title', '')
    year = params.get('year', '')
    tmdb_id = params.get('id', '')
    media_type = params.get('media_type', 'movie')
    season = params.get('season', '')
    episode = params.get('episode', '')
    current_quality = params.get('current_quality_filter', 'all')
    
    options = [
        ('All Sources', 'all'),
        ('[COLOR magenta]Torrentio Only[/COLOR]', 'torrentio'),
        ('[COLOR orchid]MediaFusion Only[/COLOR]', 'mediafusion'),
        ('[COLOR dodgerblue]Orionoid Only[/COLOR]', 'orionoid'),
        ('[COLOR yellow]Torrent Scrapers Only[/COLOR]', 'torrent'),
        ('[COLOR red]VidSrc Only (Direct)[/COLOR]', 'vidsrc'),
        ('[COLOR orange]Streaming Sites Only[/COLOR]', 'direct'),
        ('Debrid Sources Only', 'debrid'),
    ]
    
    for label, source_value in options:
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        if media_type == 'tv' and season and episode:
            url = build_url({
                'action': 'episode_sources',
                'title': title,
                'id': tmdb_id,
                'season': season,
                'episode': episode,
                'quality_filter': current_quality,
                'source_filter': source_value
            })
        else:
            url = build_url({
                'action': 'movie_sources',
                'title': title,
                'year': year,
                'id': tmdb_id,
                'quality_filter': current_quality,
                'source_filter': source_value
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def play_direct(params):
    """Play direct VidSrc stream"""
    from resources.lib import scraper
    import re
    
    stream_url = params.get('stream_url', '')
    title = params.get('title', '')
    quality = params.get('quality', '')
    
    if not stream_url:
        xbmcgui.Dialog().notification('Orion', 'Invalid stream URL', ADDON_ICON)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    log(f"Attempting to play VidSrc stream: {stream_url}")
    
    progress = xbmcgui.DialogProgress()
    progress.create('Orion', 'Extracting stream from VidSrc...')
    
    try:
        # VidSrc provides embed URLs - try to extract the actual stream
        progress.update(20, 'Fetching embed page...')
        
        # Try to extract m3u8 URL from embed
        extracted_url = scraper._extract_vidsrc_stream(stream_url)
        
        if extracted_url:
            progress.update(80, 'Stream found, starting playback...')
            log(f"Extracted stream URL: {extracted_url}")
            
            li = xbmcgui.ListItem(path=extracted_url)
            li.setInfo('video', {'title': title})
            
            # Set inputstream.adaptive for HLS streams
            if '.m3u8' in extracted_url:
                li.setProperty('inputstream', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.manifest_type', 'hls')
                li.setMimeType('application/vnd.apple.mpegurl')
                li.setContentLookup(False)
            
            progress.close()
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
            return
        
        # Fallback: Try using the embed URL directly with web player approach
        progress.update(60, 'Trying alternative playback method...')
        
        # Some Kodi installations can handle embed URLs via inputstream.ffmpegdirect
        li = xbmcgui.ListItem(path=stream_url)
        li.setInfo('video', {'title': title})
        
        # Try inputstream.ffmpegdirect for web embeds
        if xbmc.getCondVisibility('System.HasAddon(inputstream.ffmpegdirect)'):
            li.setProperty('inputstream', 'inputstream.ffmpegdirect')
            li.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
            li.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
            progress.close()
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
            return
        
        progress.close()
        
        # Last resort: Show dialog with instructions
        xbmcgui.Dialog().ok(
            'VidSrc Stream', 
            f'Could not extract direct stream URL.\n\n'
            f'The embed URL is:\n[COLOR cyan]{stream_url}[/COLOR]\n\n'
            f'Try using a browser or ResolveURL addon.'
        )
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        
    except Exception as e:
        progress.close()
        log(f"VidSrc playback error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Orion', f'Playback failed: {str(e)[:50]}', ADDON_ICON)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

def play_source(params):
    """Resolve and play source via debrid"""
    from resources.lib import resolver
    
    magnet = params.get('magnet', '')
    title = params.get('title', '')
    
    if not magnet:
        xbmcgui.Dialog().notification('Orion', 'Invalid source', ADDON_ICON)
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create('Orion', 'Resolving link via debrid...')
    
    try:
        stream_url = resolver.resolve_magnet(magnet, progress)
        progress.close()
        
        if stream_url:
            li = xbmcgui.ListItem(path=stream_url)
            li.setInfo('video', {'title': title})
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
        else:
            xbmcgui.Dialog().notification('Orion', 'Failed to resolve link', ADDON_ICON)
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
    except Exception as e:
        progress.close()
        log(f"Error resolving: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Orion', f'Error: {str(e)}', ADDON_ICON)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

def trakt_menu():
    """Trakt integration menu"""
    if not ADDON.getSetting('trakt_token'):
        add_directory_item("[COLOR red]Trakt Not Authorized - Click to Authorize[/COLOR]", {'action': 'pair_trakt'}, False)
    else:
        items = [
            ("[B]My Watchlist - Movies[/B]", {'action': 'trakt_list', 'list': 'watchlist', 'type': 'movies'}),
            ("[B]My Watchlist - TV Shows[/B]", {'action': 'trakt_list', 'list': 'watchlist', 'type': 'shows'}),
            ("[B]Trending Movies[/B]", {'action': 'trakt_list', 'list': 'trending', 'type': 'movies'}),
            ("[B]Trending TV Shows[/B]", {'action': 'trakt_list', 'list': 'trending', 'type': 'shows'}),
            ("[B]Popular Movies[/B]", {'action': 'trakt_list', 'list': 'popular', 'type': 'movies'}),
            ("[B]Popular TV Shows[/B]", {'action': 'trakt_list', 'list': 'popular', 'type': 'shows'}),
            ("[COLOR yellow]Re-authorize Trakt[/COLOR]", {'action': 'pair_trakt'}, False),
        ]
        
        for item in items:
            if len(item) == 3:
                add_directory_item(item[0], item[1], item[2])
            else:
                add_directory_item(item[0], item[1])
    
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_list(params):
    """Display Trakt list"""
    from resources.lib import trakt, tmdb
    
    list_type = params.get('list', 'watchlist')
    media_type = params.get('type', 'movies')
    
    trakt_api = trakt.TraktAPI()
    items = trakt_api.get_list(list_type, media_type)
    
    for item in items:
        if media_type == 'movies':
            movie = item.get('movie', item)
            title = movie.get('title', 'Unknown')
            year = movie.get('year', '')
            tmdb_id = movie.get('ids', {}).get('tmdb')
            
            # Get TMDB metadata
            if tmdb_id:
                details = tmdb.get_movie_details(tmdb_id)
                poster = tmdb.get_poster_url(details.get('poster_path'))
                backdrop = tmdb.get_backdrop_url(details.get('backdrop_path'))
                plot = details.get('overview', '')
            else:
                poster = ADDON_ICON
                backdrop = ADDON_FANART
                plot = ''
            
            display = f"{title} ({year})" if year else title
            
            li = xbmcgui.ListItem(label=display)
            li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
            li.setInfo('video', {'title': title, 'year': year, 'plot': plot, 'mediatype': 'movie'})
            
            url = build_url({'action': 'movie_sources', 'id': tmdb_id, 'title': title, 'year': year})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        else:
            show = item.get('show', item)
            title = show.get('title', 'Unknown')
            year = show.get('year', '')
            tmdb_id = show.get('ids', {}).get('tmdb')
            
            if tmdb_id:
                details = tmdb.get_tv_details(tmdb_id)
                poster = tmdb.get_poster_url(details.get('poster_path'))
                backdrop = tmdb.get_backdrop_url(details.get('backdrop_path'))
                plot = details.get('overview', '')
            else:
                poster = ADDON_ICON
                backdrop = ADDON_FANART
                plot = ''
            
            display = f"{title} ({year})" if year else title
            
            li = xbmcgui.ListItem(label=display)
            li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
            li.setInfo('video', {'title': title, 'year': year, 'plot': plot, 'mediatype': 'tvshow'})
            
            url = build_url({'action': 'tv_seasons', 'id': tmdb_id, 'title': title})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def open_settings():
    """Open addon settings"""
    ADDON.openSettings()

def clear_cache():
    """Clear addon cache"""
    import os
    import xbmcvfs
    
    cache_path = xbmcvfs.translatePath(f'special://temp/{ADDON_ID}/')
    if xbmcvfs.exists(cache_path):
        import shutil
        shutil.rmtree(cache_path)
    
    xbmcgui.Dialog().notification('Orion', 'Cache cleared', ADDON_ICON)

# Route actions
params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
action = params.get('action')

log(f"Action: {action}, Params: {params}")

if not action:
    main_menu()
elif action == 'movies_menu':
    movies_menu()
elif action == 'tvshows_menu':
    tvshows_menu()
elif action == 'providers_menu':
    providers_menu(params)
elif action == 'list_by_provider':
    list_by_provider(params)
elif action == 'list_content':
    list_content(params)
elif action == 'tv_seasons':
    tv_seasons(params)
elif action == 'tv_episodes':
    tv_episodes(params)
elif action == 'search_menu':
    search_menu()
elif action == 'search':
    do_search(params)
elif action == 'search_actor':
    search_actor(params)
elif action == 'actor_works':
    actor_works(params)
elif action == 'in_cinema':
    in_cinema(params)
elif action == 'latest_episodes':
    latest_episodes(params)
elif action == 'movie_sources':
    movie_sources(params)
elif action == 'episode_sources':
    episode_sources(params)
elif action == 'play':
    play_source(params)
elif action == 'play_direct':
    play_direct(params)
elif action == 'filter_quality':
    filter_quality(params)
elif action == 'filter_source':
    filter_source(params)
elif action == 'trakt_menu':
    trakt_menu()
elif action == 'trakt_list':
    trakt_list(params)
elif action == 'open_settings':
    open_settings()
elif action == 'clear_cache':
    clear_cache()
# Debrid pairing actions
elif action == 'pair_rd':
    from resources.lib import debrid
    debrid.RealDebrid().pair()
elif action == 'pair_pm':
    from resources.lib import debrid
    debrid.Premiumize().pair()
elif action == 'pair_ad':
    from resources.lib import debrid
    debrid.AllDebrid().pair()
elif action == 'pair_trakt':
    from resources.lib import trakt
    trakt.TraktAPI().pair()
# QR Code actions
elif action == 'qr_rd':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('Real-Debrid', 'https://real-debrid.com/device')
elif action == 'qr_pm':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('Premiumize', 'https://premiumize.me/device')
elif action == 'qr_ad':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('AllDebrid', 'https://alldebrid.com/pin')
elif action == 'qr_trakt':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('Trakt', 'https://trakt.tv/activate')
else:
    log(f"Unknown action: {action}", xbmc.LOGWARNING)
    main_menu()