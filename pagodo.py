#!/usr/bin/env python3
"""pagodo - Passive Google dork collection with safer runtime behavior."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import random
import re
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

import yagooglesearch

__version__ = "2.8.0-omniscient"

DEFAULT_IGNORED_URL_PREFIXES = (
    "https://www.kb.cert.org",
    "https://www.exploit-db.com/",
    "https://twitter.com/ExploitDB/",
    "https://x.com/ExploitDB/",
)


class PagodoError(RuntimeError):
    """Expected pagodo runtime error."""


class Pagodo:
    """Run passive Google dork searches and persist structured results."""

    def __init__(
        self,
        google_dorks_file: str,
        domain: str = "",
        max_search_result_urls_to_return_per_dork: int = 100,
        save_pagodo_results_to_json_file: str | bool | None = False,
        proxies: str = "",
        proxies_file: str = "",
        save_urls_to_file: str | bool | None = False,
        minimum_delay_between_dork_searches_in_seconds: float = 37,
        maximum_delay_between_dork_searches_in_seconds: float = 60,
        disable_verify_ssl: bool = False,
        verbosity: int = 4,
        specific_log_file_name: str = "pagodo.py.log",
        output_directory: str = ".",
        continue_on_error: bool = True,
        no_sleep: bool = False,
    ) -> None:
        self.stop_requested = False
        self.output_directory = Path(output_directory).expanduser().resolve()
        self.output_directory.mkdir(parents=True, exist_ok=True)

        self.log = self._build_logger(specific_log_file_name, verbosity)
        self.verbosity = verbosity
        self.disable_verify_ssl = disable_verify_ssl
        self.continue_on_error = continue_on_error
        self.no_sleep = no_sleep

        self.google_dorks_file = Path(google_dorks_file).expanduser().resolve()
        self._validate_inputs(
            minimum_delay_between_dork_searches_in_seconds,
            maximum_delay_between_dork_searches_in_seconds,
            max_search_result_urls_to_return_per_dork,
        )

        self.google_dorks = self._load_nonempty_lines(self.google_dorks_file)
        if not self.google_dorks:
            raise PagodoError(f"No Google dorks found in {self.google_dorks_file}")

        self.domain = domain.strip()
        self.max_search_result_urls_to_return_per_dork = (
            max_search_result_urls_to_return_per_dork
        )
        self.minimum_delay = minimum_delay_between_dork_searches_in_seconds
        self.maximum_delay = maximum_delay_between_dork_searches_in_seconds
        self.proxies = self._load_proxies(proxies, proxies_file)
        self.proxy_rotation_index = 0
        self.total_urls_found = 0
        self.unique_urls: set[str] = set()

        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_file_name = f"pagodo_results_{stamp}"
        self.save_pagodo_results_to_json_file = self._resolve_output_path(
            save_pagodo_results_to_json_file, ".json"
        )
        self.save_urls_to_file = self._resolve_output_path(save_urls_to_file, ".txt")

        self.delay_between_dork_searches_list = sorted(
            round(random.uniform(self.minimum_delay, self.maximum_delay), 1)
            for _ in range(20)
        )

        self.pagodo_results_dict: dict[str, Any] = {}
        self._install_signal_handlers()

    def _build_logger(self, log_name: str, verbosity: int) -> logging.Logger:
        if verbosity not in range(0, 6):
            raise PagodoError("Verbosity must be between 0 and 5")

        logger = logging.getLogger(f"pagodo.{id(self)}")
        logger.propagate = False
        logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

        log_path = Path(log_name).expanduser()
        if not log_path.is_absolute():
            log_path = self.output_directory / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.setLevel((6 - verbosity) * 10 if verbosity else logging.NOTSET)
        return logger

    def _validate_inputs(self, minimum: float, maximum: float, max_urls: int) -> None:
        if not self.google_dorks_file.is_file():
            raise PagodoError(
                f"Specify a valid file containing Google dorks with -g: {self.google_dorks_file}"
            )
        if minimum < 0 or maximum < 0:
            raise PagodoError("Delay values must be zero or greater")
        if maximum < minimum:
            raise PagodoError("Maximum delay (-x) must be greater than or equal to minimum delay (-i)")
        if max_urls <= 0:
            raise PagodoError("Maximum URLs per dork (-m) must be greater than zero")

    @staticmethod
    def _load_nonempty_lines(path: Path) -> list[str]:
        lines: list[str] = []
        seen: set[str] = set()
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or line in seen:
                    continue
                seen.add(line)
                lines.append(line)
        return lines

    def _load_proxies(self, inline: str, proxies_file: str) -> list[str | None]:
        values: list[str] = []
        values.extend(part.strip() for part in inline.split(",") if part.strip())

        if proxies_file:
            path = Path(proxies_file).expanduser().resolve()
            if not path.is_file():
                raise PagodoError(f"Proxy file does not exist: {path}")
            values.extend(self._load_nonempty_lines(path))

        deduplicated = list(dict.fromkeys(values))
        return deduplicated if deduplicated else [None]

    def _resolve_output_path(
        self, requested: str | bool | None, suffix: str
    ) -> Path | None:
        if requested is False:
            return None
        if requested is None or requested is True:
            return self.output_directory / f"{self.base_file_name}{suffix}"

        path = Path(str(requested)).expanduser()
        if not path.is_absolute():
            path = self.output_directory / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    def _install_signal_handlers(self) -> None:
        def request_stop(signum: int, _frame: Any) -> None:
            self.stop_requested = True
            self.log.warning("Signal %s received; finishing the current operation", signum)

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)

    def _next_proxy(self) -> str | None:
        proxy = self.proxies[self.proxy_rotation_index % len(self.proxies)]
        self.proxy_rotation_index += 1
        return proxy

    @staticmethod
    def _normalize_query(query: str) -> tuple[str, str | None]:
        words = query.split()
        if len(words) <= 32:
            return query, None

        ignored = " ".join(words[32:])
        updated = " ".join(words[:32])
        if query.endswith('"') and not updated.endswith('"'):
            updated += '"'
        return updated, ignored

    @staticmethod
    def _filter_urls(urls: Iterable[str]) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for raw_url in urls:
            url = str(raw_url).strip()
            if not url or url in seen:
                continue
            if any(
                re.search(re.escape(prefix), url, re.IGNORECASE)
                for prefix in DEFAULT_IGNORED_URL_PREFIXES
            ):
                continue
            seen.add(url)
            clean.append(url)
        return clean

    @staticmethod
    def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _append_text_results(self, dork: str, urls: list[str]) -> None:
        if not self.save_urls_to_file:
            return
        with self.save_urls_to_file.open("a", encoding="utf-8") as handle:
            handle.write(f"# {dork}\n")
            handle.writelines(f"{url}\n" for url in urls)
            handle.write("#" * 50 + "\n")

    def _checkpoint(self) -> None:
        if self.save_pagodo_results_to_json_file:
            self._atomic_json_write(
                self.save_pagodo_results_to_json_file, self.pagodo_results_dict
            )

    def go(self) -> dict[str, Any]:
        initiation_timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        total_dorks = len(self.google_dorks)
        self.log.info("Initiation timestamp: %s", initiation_timestamp)

        self.pagodo_results_dict = {
            "version": __version__,
            "domain": self.domain,
            "dorks_file": str(self.google_dorks_file),
            "dorks": {},
            "unique_urls": [],
            "total_urls_found": 0,
            "initiation_timestamp": initiation_timestamp,
            "completion_timestamp": "",
            "interrupted": False,
        }

        for index, original_dork in enumerate(self.google_dorks, start=1):
            if self.stop_requested:
                self.pagodo_results_dict["interrupted"] = True
                break

            result = {"query": "", "urls_size": 0, "urls": [], "error": ""}
            self.pagodo_results_dict["dorks"][original_dork] = result

            try:
                raw_query = (
                    f"site:{self.domain} {original_dork}" if self.domain else original_dork
                )
                query, ignored = self._normalize_query(raw_query)
                result["query"] = query
                if ignored:
                    self.log.warning("Google query truncated to 32 words; removed: %r", ignored)

                proxy = self._next_proxy()
                client = yagooglesearch.SearchClient(
                    query,
                    tbs="li:1",
                    num=100,
                    max_search_result_urls_to_return=(
                        self.max_search_result_urls_to_return_per_dork
                    ),
                    proxy=proxy,
                    verify_ssl=not self.disable_verify_ssl,
                    verbosity=self.verbosity,
                )
                client.assign_random_user_agent()

                self.log.info(
                    "Search (%d/%d) query=%r proxy=%r user_agent=%r",
                    index,
                    total_dorks,
                    query,
                    proxy or "direct",
                    client.user_agent,
                )

                urls = self._filter_urls(client.search() or [])
                result["urls"] = urls
                result["urls_size"] = len(urls)
                self.total_urls_found += len(urls)
                self.unique_urls.update(urls)

                self.log.info("Results: %d URLs found for dork: %s", len(urls), original_dork)
                if urls:
                    self.log.debug("URLs:\n%s", "\n".join(urls))
                    self._append_text_results(original_dork, urls)

            except Exception as exc:  # third-party client exposes multiple exception types
                result["error"] = f"{type(exc).__name__}: {exc}"
                self.log.exception("Error with dork %r", original_dork)
                if type(exc).__name__ == "SSLError" and not self.disable_verify_ssl:
                    self.log.error("For a trusted self-signed HTTPS proxy, retry with -l")
                if not self.continue_on_error:
                    self._checkpoint()
                    raise

            self.pagodo_results_dict["total_urls_found"] = self.total_urls_found
            self.pagodo_results_dict["unique_urls"] = sorted(self.unique_urls)
            self._checkpoint()

            if index < total_dorks and not self.stop_requested and not self.no_sleep:
                pause_time = random.choice(self.delay_between_dork_searches_list)
                self.log.info("Sleeping %.1f seconds before the next search", pause_time)
                time.sleep(pause_time)

        completion_timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        self.pagodo_results_dict["completion_timestamp"] = completion_timestamp
        self.pagodo_results_dict["total_urls_found"] = self.total_urls_found
        self.pagodo_results_dict["unique_urls"] = sorted(self.unique_urls)
        self._checkpoint()

        self.log.info(
            "Completed %d configured dorks; %d result rows, %d unique URLs",
            total_dorks,
            self.total_urls_found,
            len(self.unique_urls),
        )
        self.log.info("Completion timestamp: %s", completion_timestamp)
        return self.pagodo_results_dict


class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text: str, width: int) -> list[str]:
        if text.startswith("R|"):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"pagodo - Passive Google Dork v{__version__}",
        formatter_class=SmartFormatter,
    )
    parser.add_argument("-g", "--google-dorks-file", required=True, help="File containing one Google dork per line")
    parser.add_argument("-d", "--domain", default="", help="Optional domain scope")
    parser.add_argument("-i", "--minimum-delay-between-dork-searches", dest="minimum_delay_between_dork_searches_in_seconds", type=float, default=37)
    parser.add_argument("-x", "--maximum-delay-between-dork-searches", dest="maximum_delay_between_dork_searches_in_seconds", type=float, default=60)
    parser.add_argument("-l", "--disable-ssl-verification", dest="disable_verify_ssl", action="store_true")
    parser.add_argument("-m", "--max-search-urls-to-return-per-dork", dest="max_search_result_urls_to_return_per_dork", type=int, default=100)
    parser.add_argument("-p", "--proxies", default="", help="Comma-separated proxy URLs")
    parser.add_argument("--proxies-file", default="", help="File containing one proxy URL per line")
    parser.add_argument("-o", "--json-results-file", nargs="?", metavar="JSON_FILE", dest="save_pagodo_results_to_json_file", const=None, default=False)
    parser.add_argument("-s", "--text-results-file", nargs="?", metavar="URL_FILE", dest="save_urls_to_file", const=None, default=False)
    parser.add_argument("--output-directory", default=".", help="Base directory for relative logs and result files")
    parser.add_argument("--fail-fast", dest="continue_on_error", action="store_false", help="Stop on the first failed dork")
    parser.add_argument("--no-sleep", action="store_true", help="Skip delays; intended only for controlled testing")
    parser.add_argument("-v", "--verbosity", type=int, choices=range(0, 6), default=4)
    parser.add_argument("-z", "--log", dest="specific_log_file_name", default="pagodo.py.log")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        Pagodo(**vars(args)).go()
        return 0
    except PagodoError as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
