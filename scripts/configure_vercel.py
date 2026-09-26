"""
scripts/configure_vercel.py — Safe Dynamic Vercel Configuration Adapter

Ensures vercel.json contains the correct routing without committing hardcoded
or unverified production backend URLs to the repository.

Excludes /api/* from the SPA catch-all fallback so unconfigured API requests
return an explicit 404 instead of serving HTML.

Usage:
    python3 scripts/configure_vercel.py [--backend-url https://api.example.com]

Environment variables:
    BACKEND_URL: Base URL of the dedicated backend (e.g. https://tender-saathi-api.onrender.com)
    VITE_API_URL: Direct client API URL (e.g. https://tender-saathi-api.onrender.com/api)
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from urllib.parse import urlparse
from typing import Dict, Any, List

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERCEL_JSON_PATH = os.path.join(ROOT_DIR, "vercel.json")

# Regex pattern excluding /api and /api/* from SPA catch-all rewrite
SPA_FALLBACK_SOURCE = "/((?!api(?:/|$)).*)"


def get_base_vercel_config() -> Dict[str, Any]:
    return {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "buildCommand": "python3 scripts/configure_vercel.py && npm --prefix frontend install && npm --prefix frontend run build",
        "outputDirectory": "frontend/dist",
        "framework": "vite",
        "rewrites": [
            {
                "source": SPA_FALLBACK_SOURCE,
                "destination": "/index.html"
            }
        ]
    }


def validate_backend_url(url: str) -> str:
    cleaned = url.strip().rstrip("/")
    if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid backend URL: '{url}'. Must be a valid http or https URL.")
    return cleaned


def configure_vercel(backend_url: str | None = None) -> None:
    raw_backend = (backend_url or os.environ.get("BACKEND_URL", "")).strip()
    vite_api = os.environ.get("VITE_API_URL", "").strip()

    target_backend = validate_backend_url(raw_backend) if raw_backend else ""

    config = get_base_vercel_config()
    if os.path.exists(VERCEL_JSON_PATH):
        try:
            with open(VERCEL_JSON_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if isinstance(existing, dict):
                    # Preserve top-level keys other than rewrites
                    for k, v in existing.items():
                        if k != "rewrites":
                            config[k] = v
        except Exception as e:
            print(f"[configure_vercel] Warning: reading existing vercel.json failed ({e}), regenerating default.")

    rewrites: List[Dict[str, str]] = []

    if target_backend:
        print(f"[configure_vercel] Routing /api/* to dedicated backend: {target_backend}")
        rewrites.append({
            "source": "/api/:path*",
            "destination": f"{target_backend}/api/:path*"
        })
    elif vite_api:
        print(f"[configure_vercel] VITE_API_URL configured ({vite_api}). Direct browser-to-backend communication enabled.")
    else:
        print(
            "[configure_vercel] NOTICE: Neither BACKEND_URL nor VITE_API_URL is set.\n"
            "  /api/* routes are safely excluded from the SPA fallback to prevent HTML error responses.\n"
            "  Set BACKEND_URL or VITE_API_URL in deployment environment variables to connect the backend."
        )

    # Ensure SPA fallback rewrite is always present at the end, strictly excluding /api and /api/*
    rewrites.append({
        "source": SPA_FALLBACK_SOURCE,
        "destination": "/index.html"
    })

    config["rewrites"] = rewrites
    config["buildCommand"] = "python3 scripts/configure_vercel.py && npm --prefix frontend install && npm --prefix frontend run build"
    config["outputDirectory"] = "frontend/dist"
    config["framework"] = "vite"

    with open(VERCEL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    print(f"[configure_vercel] Successfully wrote {VERCEL_JSON_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure vercel.json routing for Tender Saathi.")
    parser.add_argument("--backend-url", type=str, default=None, help="Dedicated backend URL")
    args = parser.parse_args()
    try:
        configure_vercel(args.backend_url)
    except Exception as err:
        print(f"[configure_vercel] Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
