"""
Torrent Organizer - Moves .torrent files into movies/ or shows/ folders.

Uses season pattern detection (S01, S02, etc.) and TMDb API lookups
to classify torrents as movies or TV shows. Supports Hungarian and
English torrent names.

Usage:
    python organize.py                          # dry-run (preview only)
    python organize.py --run                    # actually move files
    python organize.py --tmdb-key YOUR_KEY      # use TMDb for ambiguous titles
    python organize.py --run --tmdb-key YOUR_KEY
"""

import os
import re
import sys
import shutil
import argparse
import time

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TORRENTS_DIR = os.path.join(BASE_DIR, "torrents")
MOVIES_DIR = os.path.join(BASE_DIR, "movies")
SHOWS_DIR = os.path.join(BASE_DIR, "shows")

TMDB_BASE = "https://api.themoviedb.org/3"

# Season pattern: S01, S02, S01-S03, S01E01, etc.
SEASON_RE = re.compile(r'(?<![a-zA-Z])S\d{2}', re.IGNORECASE)

# Quality/source markers that signal the end of the title
QUALITY_RE = re.compile(
    r'\b('
    r'720p|1080[pi]|2160p|480p|4K|'
    r'BDRip|DVDRip|WEBRip|WEB-DL|WEBDL|BluRay|Bluray|HDTV|'
    r'REMUX|HDRip|BRRip|AMZN|NF|DSNP|HULU|HMAX|PCOK|iT|SKST|'
    r'MA|FMIO|MTVA|RTLM|CNGO|TV2|NOW'
    r')\b',
    re.IGNORECASE
)

# Noise words to strip from parsed titles
NOISE_RE = re.compile(
    r'\b('
    r'READ\s*N[Ff]O|READNFO|REPACK|REAL|REPACK|UNRATED|EXTENDED|IMAX|'
    r'HYBRID|RETAiL|RETAIL|CUSTOM|COMPLETE|DUBBED|NEW|'
    r'Open\s*Matte|Rendezoi\s*valtozat|TC'
    r')\b',
    re.IGNORECASE
)

# Year pattern
YEAR_RE = re.compile(r'\b((?:19|20)\d{2})\b')


def parse_torrent_name(filename):
    """
    Parse a torrent filename and extract:
      - title: cleaned human-readable title
      - year: release year (int or None)
      - has_season: whether a season marker (S01, etc.) was found
    """
    # Strip .torrent extension
    name = filename
    if name.lower().endswith('.torrent'):
        name = name[:-len('.torrent')]

    # Strip trailing 8-char hex hash (e.g., -dcef6956)
    name = re.sub(r'-[a-f0-9]{8}$', '', name)

    # Detect season marker before transforming
    season_match = SEASON_RE.search(name)
    has_season = season_match is not None

    # Determine if dot-separated or space-separated
    if '.' in name and name.count('.') > 2:
        clean = name.replace('.', ' ')
    else:
        clean = name

    # Find year
    year_match = YEAR_RE.search(clean)
    year = int(year_match.group(1)) if year_match else None

    # Find season position in clean string
    season_pos = SEASON_RE.search(clean)

    # Extract title: everything before season marker, year, or quality marker
    if season_pos:
        title = clean[:season_pos.start()]
    elif year_match:
        title = clean[:year_match.start()]
    else:
        qm = QUALITY_RE.search(clean)
        if qm:
            title = clean[:qm.start()]
        else:
            title = clean

    # Clean noise words
    title = NOISE_RE.sub('', title)
    title = re.sub(r'\s+', ' ', title).strip()
    # Remove trailing dash or hyphen
    title = title.rstrip(' -')

    return title, year, has_season


def search_tmdb(title, year, api_key):
    """
    Search TMDb multi-search to determine media type.
    Tries Hungarian first, then English.
    Returns 'movie', 'tv', or None.
    """
    for lang in ['hu-HU', 'en-US']:
        params = {
            'api_key': api_key,
            'query': title,
            'language': lang,
        }
        if year:
            params['year'] = year

        try:
            resp = requests.get(f"{TMDB_BASE}/search/multi", params=params, timeout=10)
            if resp.status_code == 429:
                # Rate limited - wait and retry
                time.sleep(1)
                resp = requests.get(f"{TMDB_BASE}/search/multi", params=params, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                for r in results:
                    mtype = r.get('media_type')
                    if mtype in ('movie', 'tv'):
                        return mtype
        except requests.RequestException:
            pass

    # Retry without year if we had one (sometimes year mismatch)
    if year:
        for lang in ['hu-HU', 'en-US']:
            params = {
                'api_key': api_key,
                'query': title,
                'language': lang,
            }
            try:
                resp = requests.get(f"{TMDB_BASE}/search/multi", params=params, timeout=10)
                if resp.status_code == 200:
                    results = resp.json().get('results', [])
                    for r in results:
                        mtype = r.get('media_type')
                        if mtype in ('movie', 'tv'):
                            return mtype
            except requests.RequestException:
                pass

    return None


def classify_torrent(filename, api_key=None):
    """
    Classify a torrent file as 'movie' or 'show'.
    Returns (category, title, year, method) where method describes how it was classified.
    """
    title, year, has_season = parse_torrent_name(filename)

    # Strong signal: season marker → TV show
    if has_season:
        return 'show', title, year, 'season-pattern'

    # If TMDb API key provided, look it up
    if api_key:
        result = search_tmdb(title, year, api_key)
        if result == 'tv':
            return 'show', title, year, 'tmdb-lookup'
        elif result == 'movie':
            return 'movie', title, year, 'tmdb-lookup'

    # Default: no season marker and no TMDb match → movie
    # This is a safe default because TV shows in torrent names
    # almost always include season markers
    return 'movie', title, year, 'default (no season marker)'


def organize(dry_run=True, api_key=None):
    """Main organizer: scan torrents/ and move files to movies/ or shows/."""

    if not os.path.isdir(TORRENTS_DIR):
        print(f"ERROR: Torrents directory not found: {TORRENTS_DIR}")
        sys.exit(1)

    # Ensure target directories exist
    os.makedirs(MOVIES_DIR, exist_ok=True)
    os.makedirs(SHOWS_DIR, exist_ok=True)

    files = sorted(f for f in os.listdir(TORRENTS_DIR) if f.lower().endswith('.torrent'))

    if not files:
        print("No .torrent files found in torrents/")
        return

    print(f"Found {len(files)} torrent file(s)\n")

    if api_key:
        print("TMDb API key provided - will look up ambiguous titles\n")
    else:
        print("No TMDb API key - using pattern-based detection only")
        print("  (Get a free key at https://www.themoviedb.org/settings/api)\n")

    movies = []
    shows = []
    errors = []

    for filename in files:
        try:
            category, title, year, method = classify_torrent(filename, api_key)
            year_str = f" ({year})" if year else ""
            entry = (filename, category, title, year, method)

            if category == 'show':
                shows.append(entry)
            else:
                movies.append(entry)

            icon = "📺" if category == 'show' else "🎬"
            print(f"  {icon} [{method}] {title}{year_str}")
            print(f"     → {category}s/{filename}")

        except Exception as e:
            errors.append((filename, str(e)))
            print(f"  ❌ ERROR: {filename} → {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary: {len(movies)} movies, {len(shows)} shows, {len(errors)} errors")
    print(f"{'='*60}")

    if dry_run:
        print("\n⚠️  DRY RUN - no files were moved.")
        print("   Run with --run to actually move files.\n")
        return

    # Actually move files
    print("\nMoving files...")
    moved = 0
    for filename, category, title, year, method in movies + shows:
        src = os.path.join(TORRENTS_DIR, filename)
        dst_dir = MOVIES_DIR if category == 'movie' else SHOWS_DIR
        dst = os.path.join(dst_dir, filename)

        if os.path.exists(dst):
            print(f"  SKIP (already exists): {filename}")
            continue

        shutil.move(src, dst)
        moved += 1

    print(f"\nDone! Moved {moved} file(s).")


def main():
    parser = argparse.ArgumentParser(
        description='Organize torrent files into movies/ and shows/ folders.'
    )
    parser.add_argument(
        '--run', action='store_true',
        help='Actually move files (default is dry-run preview)'
    )
    parser.add_argument(
        '--tmdb-key', type=str, default=None,
        help='TMDb API key for looking up ambiguous titles '
             '(get one free at https://www.themoviedb.org/settings/api)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Torrent Organizer")
    print("=" * 60)
    print(f"  Torrents: {TORRENTS_DIR}")
    print(f"  Movies:   {MOVIES_DIR}")
    print(f"  Shows:    {SHOWS_DIR}")
    print(f"  Mode:     {'LIVE' if args.run else 'DRY RUN (preview)'}")
    print("=" * 60 + "\n")

    organize(dry_run=not args.run, api_key=args.tmdb_key)


if __name__ == '__main__':
    main()
