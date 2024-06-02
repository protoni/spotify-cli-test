import os
import json
import time
import click
import requests
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn

def read_credentials_file(filename):
    try:
        with open(filename, 'r') as file:
            lines = file.readlines()
            if len(lines) < 2:
                raise ValueError("Invalid credentials file. It should have at least two lines.")
            client_id = lines[0].strip()
            client_secret = lines[1].strip()
        return client_id, client_secret
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return None, None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, None

CLIENT_ID, CLIENT_SECRET = read_credentials_file('credentials.txt')

REDIRECT_URI = 'http://localhost:8888/callback'
SCOPE = 'user-read-private user-read-email user-read-playback-state user-modify-playback-state'

# Path to the cache file for storing tokens
CACHE = '.spotify_cache'

console = Console()

def get_spotify_client():
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE
    )
    return Spotify(auth_manager=auth_manager)

@click.group()
def cli():
    pass

@cli.command()
def login():
    """Log in to Spotify."""
    sp = get_spotify_client()
    user = sp.current_user()
    click.echo(f"Logged in as {user['display_name']}")

@cli.command()
@click.argument('track_uri')
def play(track_uri):
    """Play a track on Spotify."""
    sp = get_spotify_client()
    devices = sp.devices()
    active_device = None
    for device in devices['devices']:
        if device['is_active']:
            active_device = device['id']
            break

    if not active_device:
        click.echo('No active device found. Please make sure a Spotify client is open and active.')
        click.echo('Available devices:')
        for device in devices['devices']:
            click.echo(f"Device: {device['name']}, ID: {device['id']}, Type: {device['type']}, Active: {device['is_active']}")
        return

    sp.start_playback(device_id=active_device, uris=[track_uri])
    click.echo(f"Playing track: {track_uri} on device {active_device}")
    visualize_progress(sp, track_uri)

def visualize_progress(sp, track_uri):
    track_info = sp.track(track_uri)
    track_duration = track_info['duration_ms'] / 1000  # duration in seconds
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    task = progress.add_task(f"Playing {track_info['name']} by {track_info['artists'][0]['name']}", total=track_duration)
    
    with progress:
        while not progress.finished:
            current_playback = sp.current_playback()
            if current_playback and current_playback['is_playing']:
                current_position = current_playback['progress_ms'] / 1000  # progress in seconds
                progress.update(task, completed=current_position)
            time.sleep(1)

@cli.command()
def pause():
    """Pause playback on Spotify."""
    sp = get_spotify_client()
    sp.pause_playback()
    click.echo("Playback paused.")

@cli.command()
def resume():
    """Resume playback on Spotify."""
    sp = get_spotify_client()
    sp.start_playback()
    click.echo("Playback resumed.")

@cli.command()
@click.argument('volume', type=int)
def volume(volume):
    """Set the volume (0-100) on Spotify."""
    if volume < 0 or volume > 100:
        click.echo("Volume must be between 0 and 100.")
        return

    sp = get_spotify_client()
    sp.volume(volume)
    click.echo(f"Volume set to {volume}.")

@cli.command()
@click.argument('query')
def search(query):
    """Search for a track on Spotify."""
    sp = get_spotify_client()
    results = sp.search(q=query, type='track')
    for idx, track in enumerate(results['tracks']['items']):
        click.echo(f"{idx + 1}. {track['name']} by {track['artists'][0]['name']} (URI: {track['uri']})")

@cli.command()
def devices():
    """List available Spotify devices."""
    sp = get_spotify_client()
    devices = sp.devices()
    for device in devices['devices']:
        click.echo(f"Device: {device['name']}, ID: {device['id']}, Type: {device['type']}, Active: {device['is_active']}")

if __name__ == '__main__':
    cli()
