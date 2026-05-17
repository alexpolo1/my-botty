# Botty-Go

D2R Pixel Bot rewritten in Go for cross-platform support (Linux + Windows).

Based on the Python Botty project (johannes-do/botty), this is a ground-up rewrite
in Go that maintains compatibility with the same config files, templates, and run
logic while adding native Linux support.

## Features

- Cross-platform: Linux (X11/Wayland) and Windows
- Same config format as original Botty (params.ini, game.ini, shop.ini)
- Template matching with OpenCV Go bindings
- Tesseract OCR for item identification
- Human-like mouse movement (Bezier curves)
- BNIP pickit language
- All original character builds (Sorc, Paladin, Necro, Barbarian, etc.)
- All original runs (Pindle, Eldritch, Shenk, Trav, Nihlathak, Arcane, Diablo)

## Building

```bash
# Linux
go build -o botty ./cmd/botty

# Windows (from Linux with cross-compile)
GOOS=windows GOARCH=amd64 go build -o botty.exe ./cmd/botty
```

## Configuration

Copy `config/` from the original Botty project. Params, routes, and character
config work identically.
