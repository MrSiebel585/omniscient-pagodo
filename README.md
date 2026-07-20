# Pagodo - Passive Google Dork

> Modern passive Google dork automation powered by **yagooglesearch**
> with an integrated GHDB scraper.

## Overview

Pagodo consists of two primary components:

-   **ghdb-scraper** (`ghdb_scraper.py`) downloads the latest Google
    Hacking Database (GHDB) from Exploit-DB and organizes dorks by
    category.
-   **pagodo** (`pagodo.py`) executes Google dork searches against an
    authorized target domain and exports discovered URLs.

## Features

-   Python 3.10+
-   Native HTTP(S) and SOCKS proxy support
-   Category-based GHDB exports
-   JSON and text output
-   Automatic output directory creation
-   Retry/error handling
-   Module and CLI usage
-   Global `ghdb-scraper` command support

## Quick Start

``` bash
ghdb-scraper \
  --save-all \
  --json \
  --individual-categories \
  --output-directory state/pagodo/dorks

pagodo \
  -d example.com \
  -g state/pagodo/dorks/categories/11_network_or_vulnerability_data.dorks \
  -m 5 \
  -o \
  -s
```

## GHDB Categories

    ID Category
  ---- --------------------------------
     1 Footholds
     2 Files Containing Usernames
     3 Sensitive Directories
     4 Web Server Detection
     5 Vulnerable Files
     6 Vulnerable Servers
     7 Error Messages
     8 Files Containing Juicy Info
     9 Files Containing Passwords
    10 Sensitive Online Shopping Info
    11 Network or Vulnerability Data
    12 Pages Containing Login Portals
    13 Various Online Devices
    14 Advisories and Vulnerabilities

## Installation

``` bash
git clone https://github.com/opsdisk/pagodo.git
cd pagodo
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools
pip install -r requirements.txt
```

## Generate GHDB Database

``` bash
ghdb-scraper \
  --save-all \
  --json \
  --individual-categories \
  --output-directory dorks
```

## Run Pagodo

``` bash
pagodo \
  -d authorized.example \
  -g dorks/categories/11_network_or_vulnerability_data.dorks \
  -m 3 \
  -o \
  -s
```

## Omniscient Integration

Recommended layout:

``` text
/opt/omniscient/
├── state/pagodo/dorks
├── results/pagodo
└── logs/pagodo
```

Example:

``` bash
ghdb-scraper \
  --output-directory /opt/omniscient/state/pagodo/dorks

pagodo \
  -g /opt/omniscient/state/pagodo/dorks/categories/08_files_containing_juicy_info.dorks \
  --output-directory /opt/omniscient/results/pagodo
```

## Troubleshooting

-   HTTP 429: increase delays or use proxies.
-   SSL errors: retry with SSL verification disabled if appropriate.
-   Missing `yagooglesearch`: install project requirements.
-   Permission errors: verify output directories are writable.

## License

GNU GPL v3.0.
