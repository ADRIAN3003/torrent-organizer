# 🎬 Torrent Organizer

Automatically organize your torrent files into **movies** and **shows** directories. Supports obscure Hungarian and English titles with intelligent pattern detection and optional TMDb API lookup.

## Features

✨ **Smart Classification**
- Detects TV shows by season markers (`S01`, `S02`, `S03E06`, etc.)
- Classifies everything else as movies by default
- Optional TMDb API lookups for ambiguous titles in Hungarian & English

🌍 **International Support**
- Handles both dot-separated: `A.Minecraft.Movie.2025...`
- And space-separated names: `Bukós szakasz 2160p...`, `Üvegtigris 1080i...`
- Cleans noise words: `READ NFO`, `REPACK`, `UNRATED`, `EXTENDED`, etc.

🔒 **Safe by Default**
- Dry-run mode shows preview before moving anything
- Prevents overwriting existing files
- Clean error handling

⚡ **Fast & Dependency-Light**
- Minimal dependencies (just `requests` for optional API)
- Pattern-based detection works offline
- Processes 263+ torrents instantly

## Requirements

- **Python 3.7+**
- **requests** library (for optional TMDb API feature)

## Installation

### 1. Clone or download the script

```bash
cd c:\Users\Adrian\torrent-organizer
```

### 2. Install dependencies

```bash
pip install requests
```

That's it! No additional setup needed for basic use.

## Quick Start

### Preview (Safe Dry-Run)

See what will happen **without** moving anything:

```bash
python organize.py
```

Output:
```
============================================================
  Torrent Organizer
============================================================
  Torrents: C:\Users\Adrian\torrent-organizer\torrents
  Movies:   C:\Users\Adrian\torrent-organizer\movies
  Shows:    C:\Users\Adrian\torrent-organizer\shows
  Mode:     DRY RUN (preview)
============================================================

Found 263 torrent file(s)

No TMDb API key - using pattern-based detection only
  (Get a free key at https://www.themoviedb.org/settings/api)

  🎬 [default (no season marker)] A Christmas Carol (2009)
     → movies/A.Christmas.Carol.2009.Bluray.1080p.DUBBED.DTS.HUN.x264-Girnyo-dcef6956.torrent
  📺 [season-pattern] A mi kis falunk
     → shows/A.mi.kis.falunk.S07.1080p.RTLM.WEB-DL.AAC2.0.H.264.HUN-FULCRUM-ec8e31dd.torrent
  
  ...

============================================================
Summary: 196 movies, 67 shows, 0 errors
============================================================

⚠️  DRY RUN - no files were moved.
   Run with --run to actually move files.
```

### Actually Move Files

Once you're confident with the preview, move the files:

```bash
python organize.py --run
```

Files will be moved to:
- `movies/` — all movies
- `shows/` — all TV series

### With TMDb API (Optional)

For better accuracy on ambiguous titles, get a free [TMDb API key](https://www.themoviedb.org/settings/api) and use:

```bash
python organize.py --run --tmdb-key YOUR_API_KEY
```

The organizer will:
1. Try pattern detection first (fast, offline)
2. Fall back to TMDb lookups for anything unclassified
3. Search in both Hungarian (hu-HU) and English (en-US)

## How It Works

### 1. **Season Pattern Detection** (Primary)

Files containing season markers are classified as **TV shows**:
- `S01`, `S02`, `S07` → shows
- `S01E01`, `S24E06` → shows
- `S01-S06` → shows

All TV torrents in your collection include these markers, so this catches ~99% of cases instantly.

### 2. **Title Parsing**

Extracts human-readable titles by:
- Stripping `.torrent` extension and trailing hex hash (`-dcef6956`)
- Convert dots to spaces if needed: `A.Minecraft.Movie` → `A Minecraft Movie`
- Extract quality/format markers: `720p`, `1080p`, `BluRay`, `WEB-DL`, etc.
- Remove noise: `READ NFO`, `REPACK`, `UNRATED`, etc.
- Extract year: `2025`, `1989`, etc.

Example:
```
Input:  A.mi.kis.falunk.S07.1080p.RTLM.WEB-DL.AAC2.0.H.264.HUN-FULCRUM-ec8e31dd.torrent
Parse:  title="A mi kis falunk", year=None, has_season=True
Output: Show → shows/A.mi.kis.falunk.S07...torrent
```

### 3. **TMDb API Lookup** (Optional)

For files without season markers, the script can query TMDb:
- Tries Hungarian language first, then English
- Includes year for accuracy
- Returns `movie` or `tv` classification
- Handles rate limiting automatically

## Examples

### Hungarian Movies
```
✅ A legenyanya (1989)              → movies/
✅ Csupasz pisztoly a (z)urben      → movies/
✅ Hogyan tudnek elni nelkuled      → movies/
✅ Üvegtigris 1080i                 → movies/
✅ Kegyenc fegyenc                   → movies/
```

### English Movies
```
✅ A Christmas Carol (2009)         → movies/
✅ Absolutely Anything (2015)       → movies/
✅ Ace Ventura Pet Detective        → movies/
✅ Austin Powers In Goldmember      → movies/
```

### TV Shows (All Types)
```
✅ Family Guy S01-S22               → shows/
✅ South Park S01-S26               → shows/
✅ A mi kis falunk S07              → shows/ (Hungarian show)
✅ Harmadik műszak S01-S06          → shows/ (Hungarian show)
✅ Brickleberry S01-S03             → shows/
✅ The Witcher S04                  → shows/
✅ Wednesday S02                    → shows/
```

## Command-Line Options

```bash
python organize.py [OPTIONS]

Options:
  --run                 Actually move files (default is dry-run preview)
  --tmdb-key KEY       Use TMDb API for optional title verification
  -h, --help           Show help message
```

## Troubleshooting

### Files not moving?
Make sure you use `--run` flag. By default, the script only previews.

### Missing `requests` library?
Install it:
```bash
pip install requests
```

### Want to use TMDb API?
1. Get a free key at [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
2. Create a developer account (takes ~2 minutes)
3. Copy your API key and pass it:
```bash
python organize.py --run --tmdb-key YOUR_KEY_HERE
```

### File already exists?
The organizer skips files that already exist in the destination folder.

### Misclassified file?
Files are classified based on:
1. Season pattern (`S01`, etc.) — extremely reliable
2. TMDb lookup — if API key provided
3. Default to movie — safe fallback

If you see a mismatch, the file can be moved manually, or re-run with `--tmdb-key` to enable API lookups.

## Performance

- **263 torrents**: ~0.1 seconds (pattern detection only)
- **263 torrents with TMDb**: ~10-30 seconds (depends on API response time)

Results:
- ✅ 196 movies classified
- ✅ 67 shows classified
- ✅ 0 errors

## File Structure

```
torrent-organizer/
├── organize.py          # Main script
├── README.md            # This file
├── torrents/            # Input folder (your .torrent files)
├── movies/              # Output folder (organized movies)
└── shows/               # Output folder (organized TV shows)
```

## License

Free to use and modify.

## Tips

💡 **Best Practices**
- Always run dry-run first: `python organize.py`
- Review the preview carefully before using `--run`
- Use TMDb API for maximum accuracy on obscure titles
- Back up your torrents folder before the first run (just in case!)

🐛 **Reporting Issues**
If a file is misclassified, check:
1. Does the filename contain `S01`, `S02`, etc.? (If yes, should be a show)
2. Can you find it on TMDb? (If not, might be a niche title)

---

**Happy organizing! 🎉**
