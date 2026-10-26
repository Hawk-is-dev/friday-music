from typing import Dict, List, Union
import secrets
from rapidfuzz import fuzz
from SANYAMUSIC.core.mongo import mongodb

playlistdb = mongodb.playlist

async def get_playlists(user_id: int) -> List[dict]:
    """Get all playlist objects for a user."""
    playlists = []
    async for playlist in playlistdb.find({"user_id": user_id}):
        playlists.append(playlist)
    return playlists

async def get_playlist_count(user_id: int) -> int:
    """Return the number of playlists owned by a user."""
    return await playlistdb.count_documents({"user_id": user_id})

async def is_playlist_exists(user_id: int, name: str) -> bool:
    """Check if a playlist name is already taken by the user."""
    playlist = await playlistdb.find_one({"user_id": user_id, "name": name})
    return bool(playlist)

async def get_playlist(user_id: int, name: str) -> Union[dict, bool]:
    """Retrieve playlist details by user and name."""
    playlist = await playlistdb.find_one({"user_id": user_id, "name": name})
    return playlist if playlist else False

async def get_public_playlist(playlist_id: str) -> Union[dict, bool]:
    """Retrieve a public playlist by its unique sharing ID."""
    playlist = await playlistdb.find_one({"playlist_id": playlist_id, "is_public": True})
    return playlist if playlist else False

async def save_playlist(user_id: int, name: str, songs: List[dict], is_public: bool = False):
    """Create or update a playlist for a user."""
    existing = await playlistdb.find_one({"user_id": user_id, "name": name})
    playlist_id = existing.get("playlist_id") if existing else secrets.token_hex(4)
    
    await playlistdb.update_one(
        {"user_id": user_id, "name": name},
        {
            "$set": {
                "songs": songs,
                "is_public": is_public,
                "playlist_id": playlist_id
            }
        },
        upsert=True
    )

async def delete_playlist(user_id: int, name: str) -> bool:
    """Remove a playlist from the DB."""
    res = await playlistdb.delete_one({"user_id": user_id, "name": name})
    return res.deleted_count > 0

async def add_to_playlist(user_id: int, name: str, song: dict):
    """Append a song to an existing playlist (Max 50) + Duplicate Check."""
    playlist = await get_playlist(user_id, name)
    if not playlist:
        return False
        
    songs = playlist.get("songs", [])
    if len(songs) >= 50:
        return "FULL"
        
    # Prevent Exact Duplicates (by ID)
    if any(s['vidid'] == song['vidid'] for s in songs):
        return "EXISTS"
        
    # Prevent Similar Songs (by Fuzzy Title Match > 90%)
    for s in songs:
        if fuzz.ratio(s['title'].lower(), song['title'].lower()) > 90:
            return "EXISTS"

    await playlistdb.update_one(
        {"user_id": user_id, "name": name},
        {"$push": {"songs": song}}
    )
    return True
async def remove_from_playlist(user_id: int, name: str, song_title: str):
    """Remove a specific song from a playlist by its title."""
    playlist = await get_playlist(user_id, name)
    if not playlist:
        return False
    
    songs = playlist.get("songs", [])
    updated_songs = [s for s in songs if s['title'] != song_title]
    
    if len(songs) == len(updated_songs):
        return False
        
    await playlistdb.update_one(
        {"user_id": user_id, "name": name},
        {"$set": {"songs": updated_songs}}
    )
    return True
async def add_to_playlist_by_serial(user_id: int, serial: int, song: dict):
    """Append a song to playlist indexed by serial number (1-5)."""
    playlists = await get_playlists(user_id)
    if 0 < serial <= len(playlists):
        name = playlists[serial-1]["name"]
        res = await add_to_playlist(user_id, name, song)
        if res is True:
            return name
        return res
    return False

async def toggle_public(user_id: int, name: str) -> bool:
    """Toggle Public/Private status. Returns the NEW status."""
    playlist = await playlistdb.find_one({"user_id": user_id, "name": name})
    if not playlist:
        return False
    
    new_status = not playlist.get("is_public", False)
    await playlistdb.update_one(
        {"user_id": user_id, "name": name},
        {"$set": {"is_public": new_status}}
    )
    return new_status
