# -*- coding: utf-8 -*-
"""
Link Resolver for Orion
Resolves magnet links via debrid services
"""

import xbmcaddon
import xbmc

ADDON = xbmcaddon.Addon()

def get_active_debrid():
    """Get the active debrid service based on settings"""
    from resources.lib import debrid
    
    priority = int(ADDON.getSetting('debrid_priority') or 0)
    
    services = [
        ('rd', debrid.RealDebrid),
        ('pm', debrid.Premiumize),
        ('ad', debrid.AllDebrid)
    ]
    
    # Reorder based on priority
    if priority == 1:
        services = [services[1], services[0], services[2]]
    elif priority == 2:
        services = [services[2], services[0], services[1]]
    
    # Find first enabled and authorized service
    for key, cls in services:
        enabled_setting = ADDON.getSetting(f'{key}_enabled')
        xbmc.log(f"Debrid {key}_enabled = '{enabled_setting}'", xbmc.LOGINFO)
        
        # Check if enabled (default to true for RD, false for others)
        is_enabled = enabled_setting.lower() == 'true' if enabled_setting else (key == 'rd')
        
        if is_enabled:
            service = cls()
            token = ADDON.getSetting(f'{key}_token')
            xbmc.log(f"Debrid {key} token exists: {bool(token)}", xbmc.LOGINFO)
            
            if service.is_authorized():
                xbmc.log(f"Using debrid service: {key}", xbmc.LOGINFO)
                return service
    
    # Fallback: try any authorized service regardless of enabled setting
    xbmc.log("No enabled service found, trying any authorized...", xbmc.LOGINFO)
    for key, cls in services:
        service = cls()
        if service.is_authorized():
            xbmc.log(f"Fallback to debrid service: {key}", xbmc.LOGINFO)
            return service
    
    xbmc.log("No authorized debrid service found!", xbmc.LOGERROR)
    return None

def resolve_magnet(magnet, progress=None):
    """Resolve magnet link to stream URL"""
    from resources.lib import debrid
    
    service = get_active_debrid()
    
    if not service:
        xbmc.log("No authorized debrid service found", xbmc.LOGERROR)
        return None
    
    service_name = service.__class__.__name__
    xbmc.log(f"Resolving via {service_name}", xbmc.LOGINFO)
    
    if progress:
        progress.update(5, f'Resolving via {service_name}...')
    
    return service.resolve_magnet(magnet, progress)

def filter_by_quality(sources, preferred_quality):
    """Filter sources by preferred quality"""
    quality_map = {
        '0': ['4K', '2160p'],
        '1': ['1080p'],
        '2': ['720p'],
        '3': ['SD', '480p']
    }
    
    preferred = quality_map.get(str(preferred_quality), [])
    
    if not preferred:
        return sources
    
    # Filter to preferred quality
    filtered = [s for s in sources if s.get('quality') in preferred]
    
    # If no matches, return all sources
    return filtered if filtered else sources

def auto_select_source(sources):
    """Auto-select best source based on quality and seeds"""
    if not sources:
        return None
    
    # Quality priority order
    quality_order = {'4K': 0, '2160p': 0, '1080p': 1, '720p': 2, 'SD': 3, '480p': 3, 'Unknown': 4}
    
    # Sort by quality then seeds
    sorted_sources = sorted(
        sources,
        key=lambda x: (quality_order.get(x.get('quality', 'Unknown'), 4), -x.get('seeds', 0))
    )
    
    return sorted_sources[0] if sorted_sources else None