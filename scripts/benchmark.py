import asyncio
import os
import sys

# Add the current directory to sys.path to allow importing SANYAMUSIC
sys.path.append(os.getcwd())

# Import the YouTube object from SANYAMUSIC
# Note: This will trigger the monkeypatch and initialization in SANYAMUSIC/__init__.py
from SANYAMUSIC import YouTube

# List of songs to test
SONGS = [
    "Sahiba",
    "Believer Imagine Dragons",
    "Shape of You Ed Sheeran",
    "Blinding Lights The Weeknd",
    "Dance Monkey Tones and I",
    "Stay Kid Laroi Justin Bieber",
    "Peaches Justin Bieber",
    "Levitating Dua Lipa",
    "Save Your Tears The Weeknd",
    "Dynamite BTS",
    "Bad Habits Ed Sheeran",
    "Heat Waves Glass Animals",
    "Ghost Justin Bieber",
    "Starboy The Weeknd",
    "Cold Water Major Lazer",
    "Despacito Luis Fonsi",
    "Closer The Chainsmokers",
    "Sunflower Post Malone",
    "Rockstar Post Malone",
    "Industry Baby Lil Nas X",
    "Montero Lil Nas X",
    "As It Was Harry Styles",
    "Flowers Miley Cyrus",
    "Cruel Summer Taylor Swift"
]

async def run_benchmark():
    print(f"🚀 Starting Search Benchmark ({len(SONGS)} songs)...")
    print("-" * 50)
    
    success_count = 0
    failure_count = 0
    
    for song in SONGS:
        print(f"🔍 Searching for: {song}...")
        try:
            # We use fast=True as it's the most common use case in the bot
            # This will test the Sonic API search (if configured) or the monkeypatched Local Search
            title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(song, fast=True)
            
            if title:
                print(f"✅ Found: {title}")
                print(f"   ID: {vidid} | Duration: {duration_min}")
                success_count += 1
            else:
                print(f"❌ Failed: No result found for '{song}'")
                failure_count += 1
        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")
            failure_count += 1
        print("-" * 50)

    print(f"\n📊 Benchmark Summary:")
    print(f"   Total: {len(SONGS)}")
    print(f"   Success: {success_count}")
    print(f"   Failures: {failure_count}")
    
    if failure_count == 0:
        print("\n✨ All searches passed! The system is stable.")
    else:
        print(f"\n⚠️ {failure_count} searches failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
