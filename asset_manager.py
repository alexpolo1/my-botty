"""
Botty Asset Manager - Unified asset management tool.

All-in-one tool for managing D2R template assets: capture, crop, audit,
analyze, and maintain your template library.

Commands:
  inventory         List all assets with size, dimensions, category
  audit             Find issues: duplicates, orphans, naming problems
  quality           Analyze image quality: resolution, transparency, size
  capture           Capture D2R window to screenshots/captures/
  crop X Y W H NAME Crop region from latest capture, save as template
  auto_crop         Interactive: click D2R to select a crop region
  search TERM       Find assets matching a name/pattern
  key NAME          Look up the template key to use in code
  validate          Check all templates load correctly
  similarity        Find near-duplicate images
  cleanup [--yes]   Find/remove duplicate assets
  batch OP VALUE    Batch operation: "resize WxH" or "convert png"
  help              Show this help

Examples:
  python asset_manager.py inventory
  python asset_manager.py audit
  python asset_manager.py search akara
  python asset_manager.py key akara_front
  python asset_manager.py crop 100 200 50 80 my_npc
  python asset_manager.py auto_crop
  python asset_manager.py similarity
  python asset_manager.py cleanup
  python asset_manager.py validate

Template naming convention:
  - Use lowercase_with_underscores (e.g. akara_front.png)
  - Template key is the filename uppercased (e.g. AKARA_FRONT)
  - NPC assets go in assets/npc/<name>/
  - UI templates go in assets/templates/ui/
  - Item templates go in assets/item_properties/
"""
import os, sys, argparse, json, hashlib, time, math, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# DPI awareness
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    pass

# Fix DLL loading
if sys.platform == "win32":
    _dll = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Library", "bin")
    if os.path.isdir(_dll):
        os.add_dll_directory(_dll)

import cv2
import numpy as np

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
ASSETS = BASE / "assets"

# Template directories that template_finder.py loads
TEMPLATE_DIRS = [
    "templates",
    "npc",
    "shop",
    "item_properties",
    "chests",
    "gamble",
    "items",
]

# Known NPC names for routing
NPC_NAMES = {
    'akara', 'charsi', 'kashya', 'cain', 'drognan', 'lysander',
    'fara', 'ormus', 'tyrael', 'jamella', 'halbu', 'qual_kehk',
    'malah', 'larzuk', 'anya', 'carrow', 'ashera', 'alkaar',
    'elzix', 'meshiff', 'hrrky', 'izhu', 'essjay', 'seraphina',
    'aluria', 'jermak', 'griswold', 'hugel', 'rodek', 'meathead',
    'gheed', 'act1', 'act2', 'act3', 'act4', 'act5',
}


# ===================== IMAGE UTILITIES =====================

def img_hash(path):
    """MD5 hash of image file content."""
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def img_hash_fast(path):
    """Faster hash: read first/last 4KB of file."""
    try:
        sz = os.path.getsize(path)
        with open(path, 'rb') as f:
            h = hashlib.md5(f.read(4096)).hexdigest()
            if sz > 4096:
                f.seek(-4096, 2)
                h += hashlib.md5(f.read(4096)).hexdigest()
            return h
    except:
        return None


def img_dims(path):
    """Return (w, h) or None."""
    try:
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            return None
        return img.shape[1], img.shape[0]
    except:
        return None


def img_quick_info(path):
    """Return (w, h, has_alpha) in a single image load."""
    try:
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            return None, None, False
        w, h = img.shape[1], img.shape[0]
        has_alpha = (img.shape[2] == 4 and np.min(img[:, :, 3]) < 255) if len(img.shape) > 1 and img.shape[2] >= 4 else False
        return w, h, has_alpha
    except:
        return None, None, False


def img_similarity(path1, path2):
    """Compute visual similarity between two images (0-1, higher = more similar).
    Uses resized comparison + MSE for speed."""
    try:
        img1 = cv2.imread(str(path1))
        img2 = cv2.imread(str(path2))
        if img1 is None or img2 is None:
            return 0.0
        # Resize to same size for comparison
        img1 = cv2.resize(img1, (64, 64))
        img2 = cv2.resize(img2, (64, 64))
        mse = np.mean((img1.astype('float') - img2.astype('float')) ** 2)
        return float(math.exp(-mse / 10000))
    except:
        return 0.0


# ===================== ASSET GATHERING =====================

def gather_assets(asset_dirs=None):
    """Gather all asset file paths with metadata. Uses lazy evaluation for image info."""
    if asset_dirs is None:
        asset_dirs = TEMPLATE_DIRS
    assets = {}
    for d in asset_dirs:
        dir_path = ASSETS / d
        if not dir_path.exists():
            continue
        for f in dir_path.rglob('*.png'):
            rel = str(f.relative_to(ASSETS))
            assets[rel] = {
                'path': f,
                'category': d,
                'size': f.stat().st_size,
                'dims': None,  # Lazy-loaded
                'hash': img_hash(f),
                'fast_hash': img_hash_fast(f),
                'has_alpha': False,  # Lazy-loaded
            }
    return assets


def _ensure_image_info(info):
    """Lazy-load image dimensions and alpha info if not already loaded."""
    if info['dims'] is not None:
        return
    w, h, alpha = img_quick_info(info['path'])
    info['dims'] = (w, h) if w is not None else None
    info['has_alpha'] = alpha


# ===================== COMMANDS =====================

def cmd_inventory(args):
    """List all assets with details."""
    assets = gather_assets()
    if not assets:
        print("No assets found.")
        return

    # Group by category
    cats = defaultdict(list)
    for name, info in sorted(assets.items()):
        cats[info['category']].append((name, info))

    print(f"\n{'='*70}")
    print(f"  Botty Asset Inventory ({len(assets)} assets)")
    print(f"{'='*70}\n")

    total_size = 0
    for cat in sorted(cats.keys()):
        items = cats[cat]
        cat_size = sum(i['size'] for _, i in items)
        total_size += cat_size
        print(f"  [{cat.upper()}] ({len(items)} files, {cat_size/1024:.1f} KB)")
        for name, info in items:
            _ensure_image_info(info)
            dims_str = f"{info['dims'][0]}x{info['dims'][1]}" if info['dims'] else "???"
            alpha = " [A]" if info['has_alpha'] else ""
            size_str = f"{info['size']/1024:.1f} KB" if info['size'] >= 1024 else f"{info['size']} B"
            print(f"    {name}  {dims_str}  {size_str}{alpha}")
        print()

    print(f"  Total: {len(assets)} files, {total_size/1024:.1f} KB")
    print()


def cmd_search(args):
    """Search assets by name/pattern."""
    assets = gather_assets()
    if not assets:
        print("No assets found.")
        return

    term = ' '.join(args.args).lower()

    # Exact and fuzzy matches
    results = []
    for name, info in assets.items():
        name_lower = name.lower()
        stem = Path(name).stem.lower()

        score = 0
        if term in stem:
            score = 100
        elif stem in term:
            score = 80
        elif term in name_lower:
            score = 60
        elif any(w in stem for w in term.split()):
            score = 40
        else:
            # Check with separators removed
            clean = stem.replace('_', '').replace('-', '')
            clean_term = term.replace('_', '').replace('-', '')
            if clean_term in clean:
                score = 30
            elif clean in clean_term:
                score = 20

        if score > 0:
            results.append((score, name, info))

    # Sort by score descending
    results.sort(key=lambda x: -x[0])

    print(f"\n{'='*70}")
    print(f"  Search: '{term}' ({len(results)} results)")
    print(f"{'='*70}\n")

    if not results:
        print("  No matches found.")
        # Suggest closest
        best = None
        best_dist = 999
        for name, info in assets.items():
            stem = Path(name).stem.lower()
            dist = len(set(term) - set(stem))
            if dist < best_dist and dist < len(term):
                best_dist = dist
                best = stem
        if best:
            print(f"  Closest: {best}")
    else:
        for score, name, info in results[:50]:
            _ensure_image_info(info)
            dims_str = f"{info['dims'][0]}x{info['dims'][1]}" if info['dims'] else "???"
            template_key = Path(name).stem.upper()
            alpha = " [A]" if info['has_alpha'] else ""
            print(f"    {name}  {dims_str}  key={template_key}{alpha}")
        if len(results) > 50:
            print(f"    ... and {len(results) - 50} more")

    print()


def cmd_key(args):
    """Look up the template key to use in code."""
    assets = gather_assets()
    if not assets:
        print("No assets found.")
        return

    term = ' '.join(args.args)
    if not term:
        print("  Usage: python asset_manager.py key <name>")
        print("  Example: python asset_manager.py key akara_front")
        return

    term_lower = term.lower().replace('-', '_')

    # Find matching assets
    matches = []
    for name, info in assets.items():
        stem = Path(name).stem.lower()
        if term_lower in stem or stem in term_lower:
            template_key = Path(name).stem.upper()
            matches.append((name, template_key, info))

    print(f"\n{'='*70}")
    print(f"  Template Key Lookup: '{term}'")
    print(f"{'='*70}\n")

    if not matches:
        print(f"  No assets matching '{term}'.")
        print(f"  Try: python asset_manager.py search {term}")
    else:
        for name, key, info in matches[:10]:
            _ensure_image_info(info)
            dims_str = f"{info['dims'][0]}x{info['dims'][1]}" if info['dims'] else "???"
            print(f"    {name}")
            print(f"      Key:  '{key}'")
            print(f"      Use:  template_finder.search('{key}', img, threshold=0.XX)")
            print(f"      Size: {dims_str}")
            print()
    print()


def cmd_audit(args):
    """Find asset issues: duplicates, orphans, naming problems."""
    assets = gather_assets()

    issues = []

    # 1. Find exact duplicates (same hash)
    hash_map = defaultdict(list)
    for name, info in assets.items():
        if info['hash']:
            hash_map[info['hash']].append(name)

    print(f"\n{'='*70}")
    print(f"  Botty Asset Audit")
    print(f"{'='*70}\n")

    print("  DUPLICATES (identical content):")
    dup_count = 0
    for h, names in hash_map.items():
        if len(names) > 1:
            dup_count += len(names) - 1
            print(f"    {len(names)}x: {', '.join(names)}")
    if not dup_count:
        print("    None found.")

    # 2. Naming convention issues
    print(f"\n  NAMING ISSUES:")
    naming_issues = 0
    for name, info in assets.items():
        base = Path(name).stem
        if ' ' in base:
            print(f"    {name} - contains spaces")
            naming_issues += 1
        if base != base.lower() and base != base.upper():
            print(f"    {name} - mixed case")
            naming_issues += 1
        if '_' in base and '-' in base:
            print(f"    {name} - mixed separators")
            naming_issues += 1
        # Dots in filename (not extension)
        if '.' in base and not base.endswith('.png'):
            print(f"    {name} - contains dots in name (use underscores)")
            naming_issues += 1
    if not naming_issues:
        print("    None found.")

    # 3. Oversized assets
    print(f"\n  OVERSIZED (>500x500, likely full screenshots misused as templates):")
    oversized = 0
    for name, info in assets.items():
        _ensure_image_info(info)
        if info['dims'] and (info['dims'][0] > 500 or info['dims'][1] > 500):
            print(f"    {name}  {info['dims'][0]}x{info['dims'][1]}")
            oversized += 1
    if not oversized:
        print("    None found.")

    # 4. Tiny assets
    print(f"\n  TINY (<10x10, likely corrupted or miscropped):")
    tiny = 0
    for name, info in assets.items():
        _ensure_image_info(info)
        if info['dims'] and (info['dims'][0] < 10 or info['dims'][1] < 10):
            print(f"    {name}  {info['dims'][0]}x{info['dims'][1]}")
            tiny += 1
    if not tiny:
        print("    None found.")

    # 5. Asymmetric assets (potential miscrop)
    print(f"\n  VERY ASYMMETRIC (ratio >10:1, potential miscrop):")
    asym = 0
    for name, info in assets.items():
        _ensure_image_info(info)
        if info['dims']:
            w, h = info['dims']
            ratio = max(w, h) / max(min(w, h), 1)
            if ratio > 10 and max(w, h) > 30:
                print(f"    {name}  {w}x{h}  ratio {ratio:.0f}:1")
                asym += 1
    if not asym:
        print("    None found.")

    print(f"\n  Summary: {dup_count} duplicates, {naming_issues} naming issues, "
          f"{oversized} oversized, {tiny} tiny, {asym} asymmetric")
    print()


def cmd_quality(args):
    """Analyze image quality metrics."""
    assets = gather_assets()
    if not assets:
        print("No assets found.")
        return

    print(f"\n{'='*70}")
    print(f"  Botty Asset Quality Report")
    print(f"{'='*70}\n")

    # Resolution distribution
    dims = defaultdict(int)
    for name, info in assets.items():
        _ensure_image_info(info)
        if info['dims']:
            dims[str(info['dims'][0]) + 'x' + str(info['dims'][1])] += 1

    print("  Resolution distribution (top 20):")
    for d, c in sorted(dims.items(), key=lambda x: -x[1])[:20]:
        print(f"    {d}: {c} files")
    print()

    # File size distribution
    sizes = defaultdict(int)
    for name, info in assets.items():
        bucket = info['size'] // 1024
        if bucket < 1:
            sizes['<1 KB'] += 1
        elif bucket < 10:
            sizes['1-10 KB'] += 1
        elif bucket < 50:
            sizes['10-50 KB'] += 1
        elif bucket < 100:
            sizes['50-100 KB'] += 1
        else:
            sizes['>100 KB'] += 1

    print("  File size distribution:")
    for s, c in sorted(sizes.items()):
        print(f"    {s}: {c} files")
    print()

    # Transparency usage
    alpha_count = sum(1 for info in assets.values() if info['has_alpha'])
    print(f"  With transparency (alpha): {alpha_count}/{len(assets)}")
    print()

    # Per-category stats
    print("  Per-category stats:")
    cats = defaultdict(lambda: {'count': 0, 'total_size': 0, 'avg_dims': [0, 0]})
    for name, info in assets.items():
        _ensure_image_info(info)
        c = cats[info['category']]
        c['count'] += 1
        c['total_size'] += info['size']
        if info['dims']:
            c['avg_dims'][0] += info['dims'][0]
            c['avg_dims'][1] += info['dims'][1]

    for cat in sorted(cats.keys()):
        c = cats[cat]
        avg_w = c['avg_dims'][0] // c['count'] if c['count'] else 0
        avg_h = c['avg_dims'][1] // c['count'] if c['count'] else 0
        print(f"    {cat}: {c['count']} files, {c['total_size']/1024:.1f} KB, avg {avg_w}x{avg_h}")
    print()


def find_d2r():
    """Find D2R window handle."""
    import win32gui
    import psutil
    # Find D2R process first
    d2r_pids = set()
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'D2R' in proc.info['name']:
                d2r_pids.add(proc.pid)
        except:
            pass
    
    if not d2r_pids:
        return None
    
    hwnds = []
    def cb(h, r):
        title = win32gui.GetWindowText(h)
        if 'diablo' in title.lower() and win32gui.IsWindowVisible(h):
            # Check if this window belongs to D2R process
            import win32process
            _, pid = win32process.GetWindowThreadProcessId(h)
            if pid in d2r_pids:
                r.append((h, title))
    win32gui.EnumWindows(cb, hwnds)
    
    if not hwnds:
        return None
    # Return the window with most title characters (most likely the game window)
    hwnds.sort(key=lambda x: -len(x[1]))
    return hwnds[0][0]


def grab_d2r():
    """Grab D2R client area at 1280x720."""
    from mss import mss
    import win32gui
    hwnd = find_d2r()
    if not hwnd:
        print("  [ERROR] D2R not found. Is it running and visible?")
        return None

    client = win32gui.GetClientRect(hwnd)
    w, h = client[2] - client[0], client[3] - client[1]
    screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))

    with mss() as sct:
        region = {
            'top': screen_pos[1],
            'left': screen_pos[0],
            'width': w,
            'height': h
        }
        sct_img = sct.grab(region)
        img = np.array(sct_img)[:, :, :3]

    if w != 1280 or h != 720:
        img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_LINEAR)
        print(f"  [RESIZED] {w}x{h} -> 1280x720")
    else:
        print(f"  [CAPTURED] {w}x{h}")

    return img


def cmd_capture(args):
    """Capture D2R window and save."""
    save_dir = BASE / "screenshots" / "captures"
    save_dir.mkdir(parents=True, exist_ok=True)

    img = grab_d2r()
    if img is None:
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"capture_{ts}.png"
    path = save_dir / name
    cv2.imwrite(str(path), img)
    print(f"\n  [SAVED] {path}")
    print(f"  Crop with: python asset_manager.py crop X Y W H template_name")
    print(f"  Or use:    python asset_manager.py auto_crop")
    print()


def cmd_crop(args):
    """Crop a region from the latest capture and save as template."""
    x, y, w, h = args.x, args.y, args.w, args.h
    name = args.name

    # Find latest capture or grab fresh
    save_dir = BASE / "screenshots" / "captures"
    captures = sorted(save_dir.glob("capture_*.png"), key=os.path.getmtime)
    if captures:
        img = cv2.imread(str(captures[-1]), cv2.IMREAD_UNCHANGED)
        if img is not None:
            print(f"  [LOADED] {captures[-1].name}")
        else:
            img = None

    if img is None:
        print("  No recent capture. Grabbing fresh...")
        img = grab_d2r()

    if img is None:
        return

    # Crop
    h_img, w_img = img.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w_img, x + w), min(h_img, y + h)
    crop = img[y1:y2, x1:x2]

    if crop.size == 0:
        print(f"  [ERROR] Crop region ({x},{y},{w},{h}) is out of bounds (image is {w_img}x{h_img})")
        return

    # Auto-trim black/transparent borders
    crop = _trim_borders(crop)

    # Determine save location
    save_dir, name_lower = _resolve_save_path(name)

    # Auto-number if exists
    fname = f"{name_lower}.png"
    save_path = save_dir / fname
    variant = 1
    while save_path.exists():
        variant += 1
        fname = f"{name_lower}_{variant}.png"
        save_path = save_dir / fname

    cv2.imwrite(str(save_path), crop)

    rel = str(save_path.relative_to(ASSETS))
    print(f"\n  [SAVED] {rel} ({crop.shape[1]}x{crop.shape[0]})")

    # Show template key for use in code
    template_key = fname[:-4].upper()
    print(f"  Template key: '{template_key}'")
    print(f"  Use in code:  template_finder.search('{template_key}', img, threshold=0.XX)")
    print()


def _trim_borders(img):
    """Trim black and transparent borders from an image."""
    # Handle grayscale images (1 channel)
    if len(img.shape) == 2:
        mask = (img > 1).astype(np.uint8) * 255
    elif img.shape[2] == 4:
        # RGBA: non-transparent AND non-black pixels
        alpha = img[:, :, 3]
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        mask = ((gray > 1) & (alpha > 0)).astype(np.uint8) * 255
    else:
        # BGR or other: non-black pixels
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mask = (gray > 1).astype(np.uint8) * 255

    coords = cv2.findNonZero(mask)
    if coords is None:
        return img

    x, y, w, h = cv2.boundingRect(coords)
    # Add 2px padding
    pad = 2
    h_img, w_img = img.shape[:2]
    x = max(0, x - pad)
    y = max(0, y - pad)
    w = min(w_img - x, w + 2 * pad)
    h = min(h_img - y, h + 2 * pad)

    return img[y:y+h, x:x+w]


def _resolve_save_path(name):
    """Determine where to save a new asset based on its name."""
    name_lower = name.lower().replace('-', '_').replace(' ', '_')

    if name_lower in NPC_NAMES:
        save_dir = ASSETS / "npc" / name_lower
    elif 'template' in name_lower or 'ui' in name_lower:
        save_dir = ASSETS / "templates" / "ui"
    elif 'chest' in name_lower:
        save_dir = ASSETS / "chests"
    elif 'item' in name_lower:
        save_dir = ASSETS / "item_properties"
    elif 'npc' in name_lower or 'action' in name_lower:
        save_dir = ASSETS / "npc" / "action_btn"
    elif 'gamble' in name_lower:
        save_dir = ASSETS / "gamble"
    elif 'shop' in name_lower:
        save_dir = ASSETS / "shop"
    else:
        save_dir = ASSETS / "templates"

    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir, name_lower


def cmd_auto_crop(args):
    """Interactive crop mode: click D2R to select region."""
    try:
        from input_layer import keyboard
    except ImportError:
        sys.path.insert(0, str(BASE / "src"))
        from input_layer import keyboard

    print(f"\n{'='*70}")
    print(f"  Botty Auto-Crop (Interactive)")
    print(f"{'='*70}")
    print(f"  1. Press F1 to capture D2R")
    print(f"  2. Position mouse over TOP-LEFT corner, press F2")
    print(f"  3. Position mouse over BOTTOM-RIGHT corner, press F2")
    print(f"  4. Preview shows in window - press:")
    print(f"       F3  Accept and save (you'll be prompted for name)")
    print(f"       F4  Retry selection (goes back to step 2)")
    print(f"       F12 Exit")
    print(f"  {'='*70}")
    print("  Ready. Press F1 to capture D2R.\n")

    img = None
    pt1 = None
    pt2 = None

    def on_f1():
        nonlocal img
        img = grab_d2r()
        if img is not None:
            print("  [CAPTURED] Press F2 for top-left corner.")

    def on_f2():
        nonlocal pt1, pt2
        from input_layer import mouse
        mx, my = mouse.get_position()
        # Convert to D2R client coordinates
        hwnd = find_d2r()
        if hwnd:
            import win32gui
            screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))
            cx = mx - screen_pos[0]
            cy = my - screen_pos[1]
            # Scale if needed
            if img is not None:
                h_img, w_img = img.shape[:2]
                cx = int(cx * w_img / 1280)
                cy = int(cy * h_img / 720)

        if pt1 is None:
            pt1 = (cx, cy)
            print(f"  Top-left: {pt1}. Now move mouse to bottom-right and press F2 again.")
        else:
            pt2 = (cx, cy)
            print(f"  Bottom-right: {pt2}. Preview: F3=save, F4=retry")
            _show_preview()

    def _show_preview():
        if img is None or pt1 is None or pt2 is None:
            return
        h_img, w_img = img.shape[:2]
        x1 = max(0, min(pt1[0], pt2[0]))
        y1 = max(0, min(pt1[1], pt2[1]))
        x2 = min(w_img, max(pt1[0], pt2[0]))
        y2 = min(h_img, max(pt1[1], pt2[1]))

        preview = img[y1:y2, x1:x2]
        preview = _trim_borders(preview)
        # Resize for display if too large
        disp = preview.copy()
        if max(disp.shape[:2]) > 500:
            scale = 500.0 / max(disp.shape[:2])
            disp = cv2.resize(disp, (int(disp.shape[1] * scale), int(disp.shape[0] * scale)))

        cv2.imshow("Auto-Crop Preview", disp)
        cv2.waitKey(1)
        print(f"  Preview: {preview.shape[1]}x{preview.shape[0]} (after trim)")

    def on_f3():
        nonlocal img, pt1, pt2
        if img is None or pt1 is None or pt2 is None:
            print("  [ERROR] No selection. Press F1 first, then F2 twice.")
            return
        h_img, w_img = img.shape[:2]
        x1 = max(0, min(pt1[0], pt2[0]))
        y1 = max(0, min(pt1[1], pt2[1]))
        x2 = min(w_img, max(pt1[0], pt2[0]))
        y2 = min(h_img, max(pt1[1], pt2[1]))
        crop = img[y1:y2, x1:x2]
        crop = _trim_borders(crop)

        # Ask for name
        name = input("\n  Enter template name: ").strip()
        if not name:
            name = "new_asset"
        name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

        save_dir, name_lower = _resolve_save_path(name)
        fname = f"{name_lower}.png"
        save_path = save_dir / fname
        variant = 1
        while save_path.exists():
            variant += 1
            fname = f"{name_lower}_{variant}.png"
            save_path = save_dir / fname

        cv2.imwrite(str(save_path), crop)
        cv2.destroyWindow("Auto-Crop Preview")

        rel = str(save_path.relative_to(ASSETS))
        template_key = fname[:-4].upper()
        print(f"\n  [SAVED] {rel} ({crop.shape[1]}x{crop.shape[0]})")
        print(f"  Template key: '{template_key}'")
        print(f"  Use in code:  template_finder.search('{template_key}', img, threshold=0.XX)")

        # Reset for next crop
        pt1 = pt2 = None

    def on_f4():
        nonlocal pt1, pt2
        pt1 = pt2 = None
        cv2.destroyWindow("Auto-Crop Preview")
        print("  Retry. Press F2 for top-left corner.")

    keyboard.add_hotkey('f1', on_f1)
    keyboard.add_hotkey('f2', on_f2)
    keyboard.add_hotkey('f3', on_f3)
    keyboard.add_hotkey('f4', on_f4)
    keyboard.add_hotkey('f12', lambda: (print("\n  Bye."), sys.exit(0)))

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n  Bye.")


def cmd_validate(args):
    """Validate all templates load correctly."""
    assets = gather_assets()
    print(f"\n{'='*70}")
    print(f"  Botty Template Validation")
    print(f"{'='*70}\n")

    errors = 0
    warnings = 0

    for name, info in sorted(assets.items()):
        _ensure_image_info(info)
        if info['dims'] is None:
            print(f"  [ERROR] {name} - cannot read image")
            errors += 1
        elif info['dims'][0] == 0 or info['dims'][1] == 0:
            print(f"  [ERROR] {name} - zero dimensions")
            errors += 1
        elif info['size'] == 0:
            print(f"  [ERROR] {name} - empty file")
            errors += 1
        else:
            # Check template key is usable
            template_key = Path(name).stem.upper()
            cleaned = ''.join(c for c in template_key if c not in '0123456789_')
            if not cleaned.isalpha():
                print(f"  [WARN]  {name} - key '{template_key}' contains unusual chars")
                warnings += 1

    if not errors and not warnings:
        print("  All templates are valid.")
    else:
        print(f"\n  {errors} error(s), {warnings} warning(s)")
    print()


def cmd_similarity(args):
    """Find near-duplicate images using visual similarity."""
    assets = gather_assets()
    if len(assets) < 2:
        print("Need at least 2 assets to compare.")
        return

    print(f"\n{'='*70}")
    print(f"  Botty Similarity Analysis (fast mode)")
    print(f"{'='*70}\n")
    print("  Comparing assets within each category...")
    print()

    # Group by category for faster comparison
    cats = defaultdict(list)
    for name, info in assets.items():
        cats[info['category']].append((name, info))

    pairs_found = 0
    for cat, items in cats.items():
        if len(items) < 2:
            continue

        # Quick pre-filter: only compare same-size images
        size_groups = defaultdict(list)
        for name, info in items:
            _ensure_image_info(info)
            if info['dims']:
                size_groups[(info['dims'][0], info['dims'][1])].append((name, info))

        for size, group in size_groups.items():
            if len(group) < 2:
                continue

            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    n1, i1 = group[i]
                    n2, i2 = group[j]
                    # Skip exact duplicates (those are caught by audit)
                    if i1['hash'] == i2['hash']:
                        continue
                    sim = img_similarity(i1['path'], i2['path'])
                    if sim > 0.85:
                        pairs_found += 1
                        print(f"  [{sim:.2f}] {n1}  ~=  {n2}  ({size[0]}x{size[1]})")
                    elif sim > 0.70 and cat == 'npc':
                        pairs_found += 1
                        print(f"  [{sim:.2f}] {n1}  ~=  {n2}  ({size[0]}x{size[1]})")

    if not pairs_found:
        print("  No near-duplicates found.")
    else:
        print(f"\n  {pairs_found} near-duplicate pair(s) found.")
    print()


def cmd_cleanup(args):
    """Remove duplicate assets (keep first occurrence)."""
    assets = gather_assets()
    hash_map = defaultdict(list)
    for name, info in assets.items():
        if info['hash']:
            hash_map[info['hash']].append((name, info))

    print(f"\n{'='*70}")
    print(f"  Botty Asset Cleanup")
    print(f"{'='*70}\n")

    removed = 0
    for h, items in hash_map.items():
        if len(items) > 1:
            print(f"  Duplicate group ({len(items)} files):")
            for i, (name, info) in enumerate(items):
                if i == 0:
                    print(f"    [KEEP]    {name}")
                else:
                    if args.yes:
                        os.remove(str(info['path']))
                        print(f"    [REMOVED] {name}")
                        removed += 1
                    else:
                        print(f"    [WILL REMOVE] {name}")
            print()

    if args.yes:
        print(f"  Removed {removed} duplicates.")
    else:
        print(f"  Would remove {removed} duplicates. Use --yes to actually remove.")
    print()


def cmd_batch(args):
    """Batch operations on assets."""
    operation = args.operation.lower()

    if operation == "resize":
        try:
            target_w, target_h = map(int, args.value.split('x'))
        except:
            print("  Usage: python asset_manager.py batch resize WxH")
            return

        assets = gather_assets()
        count = 0
        for name, info in assets.items():
            _ensure_image_info(info)
            if info['dims'] and (info['dims'][0] != target_w or info['dims'][1] != target_h):
                img = cv2.imread(str(info['path']), cv2.IMREAD_UNCHANGED)
                if img is not None:
                    # Use INTER_AREA for downscaling (better quality), INTER_CUBIC for upscaling
                    if target_w < info['dims'][0]:
                        interp = cv2.INTER_AREA
                    else:
                        interp = cv2.INTER_CUBIC
                    resized = cv2.resize(img, (target_w, target_h), interpolation=interp)
                    cv2.imwrite(str(info['path']), resized)
                    count += 1
        print(f"  Resized {count} assets to {target_w}x{target_h}.")

    elif operation == "convert":
        fmt = args.value.lower()
        if fmt not in ('png', 'jpg', 'jpeg'):
            print("  Supported formats: png, jpg")
            return
        assets = gather_assets()
        count = 0
        for name, info in assets.items():
            if info['path'].suffix.lower() != f'.{fmt}':
                new_path = info['path'].with_suffix(f'.{fmt}')
                img = cv2.imread(str(info['path']), cv2.IMREAD_UNCHANGED)
                if img is not None:
                    cv2.imwrite(str(new_path), img)
                    count += 1
        print(f"  Converted {count} assets to .{fmt}")

    else:
        print(f"  Unknown batch operation: {operation}")
        print(f"  Supported: resize, convert")


def print_help():
    print(f"""
{'='*70}
  Botty Asset Manager
{'='*70}

Usage: python asset_manager.py [command] [options]

Commands:
  inventory          List all assets with size, dimensions, category
  search TERM        Find assets matching a name/pattern
  key NAME           Look up the template key to use in code
  audit              Find issues: duplicates, naming, oversized, tiny
  quality            Analyze image quality: resolution, transparency, size
  similarity         Find near-duplicate images
  capture            Capture D2R window to screenshots/captures/
  crop X Y W H NAME  Crop region from latest capture, save as template
  auto_crop          Interactive: click D2R to select a crop region
  validate           Check all templates load correctly
  cleanup [--yes]    Find/remove duplicate assets
  batch OP VALUE     Batch operation: "resize WxH" or "convert png"
  help               Show this help

Examples:
  python asset_manager.py inventory
  python asset_manager.py audit
  python asset_manager.py quality
  python asset_manager.py search akara
  python asset_manager.py key akara_front
  python asset_manager.py capture
  python asset_manager.py crop 100 200 50 80 akara_front
  python asset_manager.py crop 300 400 100 120 npc_dialogue
  python asset_manager.py auto_crop
  python asset_manager.py similarity
  python asset_manager.py validate
  python asset_manager.py cleanup
  python asset_manager.py cleanup --yes
  python asset_manager.py batch resize 64x64

Template naming convention:
  - Use lowercase_with_underscores (e.g. akara_front.png)
  - Template key is the filename uppercased (e.g. AKARA_FRONT)
  - NPC assets go in assets/npc/<name>/
  - UI templates go in assets/templates/ui/
  - Item templates go in assets/item_properties/

Template Finder search paths:
""")
    for d in TEMPLATE_DIRS:
        print(f"  assets/{d}/")
    print()


def main():
    parser = argparse.ArgumentParser(description='Botty Asset Manager', add_help=False)
    parser.add_argument('command', nargs='?', default='help',
                        help='Command to run')
    parser.add_argument('args', nargs='*', help='Command arguments')
    parser.add_argument('--yes', action='store_true', help='Confirm destructive actions')

    parsed = parser.parse_args()
    cmd = parsed.command.lower()

    if cmd == 'inventory':
        cmd_inventory(parsed)
    elif cmd == 'search':
        cmd_search(parsed)
    elif cmd == 'key':
        cmd_key(parsed)
    elif cmd == 'audit':
        cmd_audit(parsed)
    elif cmd == 'quality':
        cmd_quality(parsed)
    elif cmd == 'capture':
        cmd_capture(parsed)
    elif cmd == 'crop':
        if len(parsed.args) < 5:
            print("  Usage: python asset_manager.py crop X Y W H NAME")
            print("  Example: python asset_manager.py crop 100 200 50 80 akara_front")
            return
        parsed.x = int(parsed.args[0])
        parsed.y = int(parsed.args[1])
        parsed.w = int(parsed.args[2])
        parsed.h = int(parsed.args[3])
        parsed.name = parsed.args[4]
        cmd_crop(parsed)
    elif cmd == 'auto_crop':
        cmd_auto_crop(parsed)
    elif cmd == 'validate':
        cmd_validate(parsed)
    elif cmd == 'similarity':
        cmd_similarity(parsed)
    elif cmd == 'cleanup':
        cmd_cleanup(parsed)
    elif cmd == 'batch':
        if len(parsed.args) < 2:
            print("  Usage: python asset_manager.py batch OP VALUE")
            print("  Example: python asset_manager.py batch resize 64x64")
            return
        parsed.operation = parsed.args[0]
        parsed.value = parsed.args[1]
        cmd_batch(parsed)
    else:
        print_help()


if __name__ == "__main__":
    main()
