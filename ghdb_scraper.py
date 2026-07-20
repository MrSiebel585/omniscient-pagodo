#!/usr/bin/env python3
"""Retrieve Google Hacking Database dorks from Exploit-DB."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests
import urllib3
from bs4 import BeautifulSoup

__version__ = "1.3.1"

GHDB_URL = "https://www.exploit-db.com/google-hacking-database"
OUTPUT_DIRECTORY = Path("dorks")

CATEGORIES = {
    1: "Footholds",
    2: "File Containing Usernames",
    3: "Sensitive Directories",
    4: "Web Server Detection",
    5: "Vulnerable Files",
    6: "Vulnerable Servers",
    7: "Error Messages",
    8: "File Containing Juicy Info",
    9: "File Containing Passwords",
    10: "Sensitive Online Shopping Info",
    11: "Network or Vulnerability Data",
    12: "Pages Containing Login Portals",
    13: "Various Online Devices",
    14: "Advisories and Vulnerabilities",
}

REQUEST_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "deflate, gzip, br",
    "Accept-Language": "en-US",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:60.0) "
        "Gecko/20100101 Firefox/60.0"
    ),
    "X-Requested-With": "XMLHttpRequest",
}


def extract_dork_text(url_title: str) -> str:
    """Extract the dork text from the HTML anchor stored in url_title."""
    soup = BeautifulSoup(url_title, "html.parser")
    anchor = soup.find("a")

    if anchor is None:
        raise ValueError("Missing anchor element in url_title")

    return anchor.get_text(strip=True)


def sanitize_file_name(category_name: str) -> str:
    """Convert a category name into a safe lowercase filename."""
    return (
        category_name.strip()
        .lower()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def request_ghdb_json(timeout: int = 10) -> dict[str, Any]:
    """Request and validate the GHDB JSON response."""
    print(f"[+] Requesting URL: {GHDB_URL}")

    try:
        response = requests.get(
            GHDB_URL,
            headers=REQUEST_HEADERS,
            timeout=timeout,
        )
    except requests.exceptions.SSLError:
        print("[!] SSL verification failed; retrying without certificate verification")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        response = requests.get(
            GHDB_URL,
            headers=REQUEST_HEADERS,
            timeout=timeout,
            verify=False,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"HTTP {response.status_code} while retrieving {GHDB_URL}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Exploit-DB returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected GHDB response format")

    if "recordsTotal" not in payload or "data" not in payload:
        raise RuntimeError("GHDB response is missing recordsTotal or data")

    if not isinstance(payload["data"], list):
        raise RuntimeError("GHDB data field is not a list")

    return payload


def build_dork_collections(
    json_dorks: list[dict[str, Any]],
) -> tuple[list[str], dict[int, dict[str, Any]]]:
    """Extract flat and category-organized dork collections."""
    extracted_dorks: list[str] = []
    category_dict: dict[int, dict[str, Any]] = {}

    for index, dork in enumerate(json_dorks, start=1):
        try:
            url_title = str(dork["url_title"]).replace("\t", "")
            category = dork["category"]
            category_id = int(category["cat_id"])
            category_name = str(category["cat_title"])
            extracted_dork = extract_dork_text(url_title)
        except (KeyError, TypeError, ValueError) as exc:
            print(f"[!] Skipping malformed dork record {index}: {exc}")
            continue

        normalized_dork = dict(dork)
        normalized_dork["url_title"] = url_title

        extracted_dorks.append(extracted_dork)

        category_entry = category_dict.setdefault(
            category_id,
            {
                "category_name": category_name,
                "dorks": [],
            },
        )
        category_entry["dorks"].append(normalized_dork)

    return extracted_dorks, dict(sorted(category_dict.items()))


def write_category_files(
    category_dict: dict[int, dict[str, Any]],
    output_directory: Path,
) -> None:
    """Write one .dorks file per category."""
    for category_id, category_data in category_dict.items():
        category_name = category_data["category_name"]
        dorks = category_data["dorks"]

        file_name = f"{sanitize_file_name(category_name)}.dorks"
        output_file = output_directory / file_name

        print(
            f"[*] Category {category_id} ({category_name!r}) "
            f"has {len(dorks)} dorks"
        )
        print(
            f"[*] Writing dork category {category_name!r} "
            f"to file: {output_file}"
        )

        with output_file.open("w", encoding="utf-8") as handle:
            for dork in dorks:
                try:
                    handle.write(f"{extract_dork_text(dork['url_title'])}\n")
                except (KeyError, ValueError) as exc:
                    print(
                        f"[!] Skipping malformed dork in category "
                        f"{category_id}: {exc}"
                    )


def write_json_file(
    json_dorks: list[dict[str, Any]],
    output_directory: Path,
) -> None:
    """Write the complete GHDB data list to JSON."""
    output_file = output_directory / "all_google_dorks.json"
    print(f"[*] Writing all dorks to JSON file: {output_file}")

    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(json_dorks, handle, indent=2, ensure_ascii=False)


def write_all_dorks_file(
    extracted_dorks: list[str],
    output_directory: Path,
) -> None:
    """Write all extracted dorks to a plain-text file."""
    output_file = output_directory / "all_google_dorks.txt"
    print(f"[*] Writing all dorks to text file: {output_file}")

    with output_file.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(extracted_dorks))
        handle.write("\n")


def retrieve_google_dorks(
    save_json_response_to_file: bool = False,
    save_all_dorks_to_file: bool = False,
    save_individual_categories_to_files: bool = False,
) -> dict[str, Any]:
    """Retrieve GHDB dorks and optionally write them to disk."""
    payload = request_ghdb_json()

    total_dorks = int(payload["recordsTotal"])
    json_dorks = payload["data"]

    extracted_dorks, category_dict = build_dork_collections(json_dorks)

    if (
        save_json_response_to_file
        or save_all_dorks_to_file
        or save_individual_categories_to_files
    ):
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if save_individual_categories_to_files:
        write_category_files(category_dict, OUTPUT_DIRECTORY)

    if save_json_response_to_file:
        write_json_file(json_dorks, OUTPUT_DIRECTORY)

    if save_all_dorks_to_file:
        write_all_dorks_file(extracted_dorks, OUTPUT_DIRECTORY)

    print(f"[*] Total Google dorks reported: {total_dorks}")
    print(f"[*] Total Google dorks extracted: {len(extracted_dorks)}")

    return {
        "total_dorks": total_dorks,
        "extracted_dorks": extracted_dorks,
        "category_dict": category_dict,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    epilog = f"Dork categories:\n\n{json.dumps(CATEGORIES, indent=4)}"

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            f"GHDB Scraper v{__version__} - Retrieve Google Hacking "
            f"Database dorks from {GHDB_URL}."
        ),
        epilog=epilog,
    )

    parser.add_argument(
        "-i",
        dest="save_individual_categories_to_files",
        action="store_true",
        help="Write each dork category to a separate file.",
    )
    parser.add_argument(
        "-j",
        dest="save_json_response_to_file",
        action="store_true",
        help="Save the GHDB JSON response to all_google_dorks.json.",
    )
    parser.add_argument(
        "-s",
        dest="save_all_dorks_to_file",
        action="store_true",
        help="Save all Google dorks to all_google_dorks.txt.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main() -> int:
    """Run the GHDB scraper command-line interface."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        retrieve_google_dorks(**vars(args))
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user", file=sys.stderr)
        return 130
    except (OSError, RuntimeError) as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
