from typing import Optional
from spoticli.lib.util import check_url_format, get_current_playback, wait_display_playback
from spotipy import Spotify
import click


def start_playback(sp_auth: Spotify, device: str, url: Optional[str]):
    
    if url:
        try:
            valid_url = check_url_format(url)
        except ValueError:
            click.secho("Invalid URL was provided.", fg="red")
        uri = [valid_url] if "track" in url else None
        context_uri = valid_url if "track" not in url else None
        sp_auth.start_playback(device_id=device, uris=uri, context_uri=context_uri)
    else:
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(current_playback, display=False)
        if not playback.get("resuming_disallowed"):
            sp_auth.start_playback(device_id=device)
            click.secho("Playback resumed.")
    wait_display_playback(sp_auth)
