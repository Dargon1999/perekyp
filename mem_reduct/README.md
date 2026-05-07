# Mem Reduct Module

Portable utility for memory optimization.

## Features
- Full memory statistics display.
- Multiple cleaning profiles (Light/Medium/Aggressive).
- Portable: all configs stored in `\mem_reduct\config.ini`.
- MIT Licensed.

## Build Instructions

### MinGW
```bash
g++ -O3 -Wall -shared -static -static-libgcc -static-libstdc++ -o mem_reduct.dll mem_reduct.cpp -lpsapi
```

### MSVC
```bash
cl.exe /LD /O2 mem_reduct.cpp psapi.lib /Fe:mem_reduct.dll
```

## Usage
The module is integrated into the application's "Additional" settings section.
Admin privileges are required for system cache cleaning.
