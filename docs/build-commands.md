# Build commands

Run these from the repository root with GNU Make and Node.js. On Windows use PowerShell or cmd.

- `make` / `make help`: list commands without building.
- `make desktop`: build every desktop app for this host, make its GUI95 archive, and print absolute executable/bundle paths.
- `make serve`: prepare the web version (including required WASM/assets), then start a server on a free port and print LAN links. No desktop packaging is required.
- `make distro`: build this host's desktop archives, then assemble current-version archives from other hosts into `gui95-dist/`. Set `GUI95_DIST_INPUT` to a folder of archives from Windows/macOS/Linux; subdirectories are searched. `gui95-dist/index.json` records packages and missing platforms. Assembly does not claim to compile unsupported foreign platforms.
- `make install`: build and install for the current user.

Existing explicit build/test targets remain available. `all` is an explicit build alias; it is no longer the default.
