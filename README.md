# Pagodo - Passive Google Dork

> Passive Google dork automation and GHDB management.

## Table of Contents

1.  Overview
2.  Features
3.  Architecture
4.  Installation
5.  Quick Start
6.  GHDB Scraper
7.  GHDB Categories
8.  Pagodo
9.  Proxy Support
10. Output Files
11. Omniscient Integration
12. Python API
13. Examples
14. Performance Tuning
15. Troubleshooting
16. Security & Responsible Use
17. Development
18. License

------------------------------------------------------------------------

# Overview

Pagodo is a passive reconnaissance utility that automates Google dork
searches using the Google Hacking Database (GHDB).

The project consists of two major components:

-   **ghdb_scraper.py** -- retrieves the latest GHDB from Exploit-DB and
    builds categorized dork files.
-   **pagodo.py** -- performs Google searches using those dorks and
    exports discovered URLs.

------------------------------------------------------------------------

# Features

-   Python 3
-   GHDB synchronization
-   Category-based dork organization
-   Native HTTP/HTTPS/SOCKS proxy support
-   JSON and text export
-   Global CLI support
-   Module API
-   Automatic output generation
-   Robust error handling

------------------------------------------------------------------------

# Architecture

``` text
Exploit-DB GHDB
        │
        ▼
 ghdb-scraper
        │
        ▼
all_google_dorks.txt
all_google_dorks.json
categories/*.dorks
        │
        ▼
     pagodo
        │
        ▼
 JSON Results
 TXT Results
 URL Lists
```

------------------------------------------------------------------------

# Installation

``` bash
git clone https://github.com/opsdisk/pagodo.git
cd pagodo

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip setuptools
pip install -r requirements.txt
```

------------------------------------------------------------------------

# Quick Start

``` bash
ghdb-scraper \
    --save-all \
    --json \
    --individual-categories \
    --output-directory dorks

pagodo \
    -d example.com \
    -g dorks/categories/11_network_or_vulnerability_data.dorks \
    -m 5 \
    -o \
    -s
```

------------------------------------------------------------------------

# GHDB Scraper

Produces:

-   all_google_dorks.txt
-   all_google_dorks.json
-   One file per category

Example:

``` bash
ghdb-scraper \
  --save-all \
  --json \
  --individual-categories \
  --output-directory state/pagodo/dorks
```

------------------------------------------------------------------------

# GHDB Categories

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

------------------------------------------------------------------------

# Pagodo

Typical execution:

``` bash
pagodo \
  -d authorized.example \
  -g categories/08_files_containing_juicy_info.dorks \
  -m 3 \
  -o \
  -s
```

Recommended workflow:

1.  Update GHDB.
2.  Choose category.
3.  Scope to authorized domain.
4.  Review exported results.

------------------------------------------------------------------------

# Proxy Support

Single proxy:

``` bash
-p http://proxy:8080
```

Multiple proxies:

``` bash
-p http://a:8080,socks5h://127.0.0.1:9050
```

Proxy file (if supported by your build):

``` bash
--proxies-file proxies.txt
```

------------------------------------------------------------------------

# Output Files

    results/
        results.json
        results.txt
        pagodo.log

------------------------------------------------------------------------

# Omniscient Integration

    /opt/omniscient/
        state/pagodo/dorks
        results/pagodo
        logs/pagodo

Example:

``` bash
ghdb-scraper \
 --output-directory /opt/omniscient/state/pagodo/dorks
```

``` bash
pagodo \
 -g /opt/omniscient/state/pagodo/dorks/categories/11_network_or_vulnerability_data.dorks \
 --output-directory /opt/omniscient/results/pagodo
```

------------------------------------------------------------------------

# Python API

``` python
import ghdb_scraper

data = ghdb_scraper.retrieve_google_dorks(
    save_all_dorks_to_file=True
)

print(data["total_dorks"])
```

``` python
import pagodo

pg = pagodo.Pagodo(
    google_dorks_file="dorks.txt",
    domain="example.com"
)

results = pg.go()
```

------------------------------------------------------------------------

# Performance Tuning

-   Use category files instead of all dorks.
-   Use reasonable delays.
-   Use authorized targets only.
-   Limit maximum results.
-   Rotate proxies responsibly.

------------------------------------------------------------------------

# Troubleshooting

## HTTP 429

Increase delays.

## SSL Errors

Retry with verification disabled if appropriate.

## Permissions

Ensure output directories are writable.

## Missing Dependencies

Install:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

# Security & Responsible Use

Only scan systems you own or are explicitly authorized to assess.

Google rate limiting and terms of service should be respected.

------------------------------------------------------------------------

# Development

Project layout:

    pagodo.py
    ghdb_scraper.py
    requirements.txt
    dorks/
    README.md

Recommended improvements:

-   Async requests
-   Incremental GHDB updates
-   Better reporting
-   Unit tests
-   CI pipeline

------------------------------------------------------------------------

# License

GNU GPL v3.0

------------------------------------------------------------------------

# Credits

Original project: https://github.com/opsdisk/pagodo





---

# Omniscient Integration

Pagodo integrates cleanly into the Omniscient DFIR/OSINT framework by separating **state**, **results**, and **logs**. This keeps downloaded GHDB data, search results, and runtime artifacts organized while allowing other Omniscient modules to consume the generated intelligence.

## Directory Layout

```text
/opt/omniscient/
├── state/
│   └── pagodo/
│       └── dorks/
│           ├── all_google_dorks.txt
│           ├── all_google_dorks.json
│           └── categories/
│               ├── 01_footholds.dorks
│               ├── 02_files_containing_usernames.dorks
│               ├── ...
│               └── 14_advisories_and_vulnerabilities.dorks
│
├── results/
│   └── pagodo/
│       ├── pagodo_results.json
│       ├── pagodo_results.txt
│       └── exports/
│
└── logs/
    └── pagodo/
        └── pagodo.log
```

---

## Workflow

```text
              Exploit-DB GHDB
                     │
                     ▼
              ghdb-scraper
                     │
                     ▼
    /opt/omniscient/state/pagodo/dorks
                     │
                     ▼
                 pagodo
                     │
                     ▼
   /opt/omniscient/results/pagodo
                     │
                     ▼
      Omniscient DFIR / OSINT Modules
```

---

## Step 1 — Download the Latest GHDB

Generate a fresh copy of the Google Hacking Database and organize it into categories.

```bash
ghdb-scraper \
  --save-all \
  --json \
  --individual-categories \
  --output-directory /opt/omniscient/state/pagodo/dorks
```

Generated files include:

```text
all_google_dorks.txt
all_google_dorks.json
categories/*.dorks
```

---

## Step 2 — Run Pagodo

Select the category most appropriate for your assessment.

Example using the **Network or Vulnerability Data** category:

```bash
pagodo \
  -d authorized.example \
  -g /opt/omniscient/state/pagodo/dorks/categories/11_network_or_vulnerability_data.dorks \
  --output-directory /opt/omniscient/results/pagodo \
  -m 3 \
  -o \
  -s
```

---

## Example Categories

| Category | Typical Purpose |
|-----------|-----------------|
| 01 | Initial foothold discovery |
| 02 | Exposed usernames |
| 03 | Sensitive directories |
| 04 | Web server fingerprinting |
| 05 | Vulnerable files |
| 06 | Vulnerable servers |
| 07 | Error message disclosure |
| 08 | Sensitive documents and configuration files |
| 09 | Password exposure |
| 10 | Shopping and payment information |
| 11 | Network infrastructure and vulnerability intelligence |
| 12 | Login portals |
| 13 | Internet-connected devices |
| 14 | Public advisories and known vulnerabilities |

---

## Suggested Omniscient Workflow

```text
Update GHDB
      │
      ▼
Choose Category
      │
      ▼
Scope to Authorized Domain
      │
      ▼
Execute Pagodo
      │
      ▼
Export JSON / TXT Results
      │
      ▼
Import Into
 • OSINT
 • DFIR
 • Reporting
 • Case Management
```

---

## Recommended Directory Permissions

```bash
sudo mkdir -p \
  /opt/omniscient/state/pagodo/dorks \
  /opt/omniscient/results/pagodo \
  /opt/omniscient/logs/pagodo

sudo chown -R root:omniscient \
  /opt/omniscient/state/pagodo \
  /opt/omniscient/results/pagodo \
  /opt/omniscient/logs/pagodo

sudo chmod -R 2775 \
  /opt/omniscient/state/pagodo \
  /opt/omniscient/results/pagodo \
  /opt/omniscient/logs/pagodo
```

---

## Integration Opportunities

Pagodo output can be consumed by other Omniscient components, including:

- **OSINT** for enrichment and correlation.
- **Case Management** for preserving search results as evidence.
- **Reporting** for generating assessment summaries.
- **Evidence Storage** for archiving JSON and text exports.
- **Automation Pipelines** for scheduled GHDB updates and recurring searches against authorized scopes.

Separating **state**, **results**, and **logs** makes the workflow reproducible, simplifies backups, and allows downstream modules to process Pagodo output without modifying the original GHDB data.

Modern documentation and workflow updates for current GHDB and Pagodo
usage.
