#!/usr/bin/env python3
"""Deterministically verify every image URL in an ABM page actually loads.

Replaces the manual image-verification gate. The manual check kept getting
two things wrong: (1) it dropped the `Accept: image/*` header / browser
User-Agent, so Brandfetch (and some CDNs) returned an HTML fallback page and
the model wrongly declared a valid logo "broken"; (2) it guessed at URLs.
This script bakes the correct headers in, so the model cannot get the check
wrong, and it extracts the URLs straight from the HTML so none are missed.

Usage:
    python3 verify_images.py path/to/page.html      # extract + check every image URL
    python3 verify_images.py --url https://... ...   # check specific URLs

Exit code 0 = every image loads as a real image. Non-zero = at least one is
broken (the verification gate fails — fix before saving to Folloze).
"""
import sys
import re
import ssl
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {
    "Accept": "image/avif,image/webp,image/apng,image/png,image/svg+xml,*/*",
    "User-Agent": UA,
}
TIMEOUT = 15


def _ssl_contexts():
    # Prefer real cert verification; fall back to unverified ONLY when the
    # local Python can't find a CA bundle (common on macOS) — otherwise a
    # local trust-store quirk would false-fail every valid HTTPS image,
    # which is exactly the failure mode this script exists to remove.
    try:
        import certifi
        verified = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        verified = ssl.create_default_context()
    return verified, ssl._create_unverified_context()


CTX_VERIFIED, CTX_UNVERIFIED = _ssl_contexts()


def extract_urls(html):
    urls = []
    urls += re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
    urls += re.findall(r'<source[^>]+srcset=["\']([^"\' ,]+)', html, re.I)
    urls += [m[1] for m in
             re.findall(r'background-image:\s*url\((["\']?)([^"\')]+)\1\)', html, re.I)]
    seen, out = set(), []
    for u in urls:
        u = u.strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def check(url):
    if url.startswith("data:"):
        return ("WARN", "base64/data URI — the skill forbids base64; use a real https URL")
    if not url.lower().startswith(("http://", "https://")):
        return ("BROKEN", f"not an absolute http(s) URL ({url[:70]})")
    req = urllib.request.Request(url, headers=HEADERS)
    for ctx in (CTX_VERIFIED, CTX_UNVERIFIED):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
                ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                blob = r.read(4096)
                if ctype.startswith("image/"):
                    return ("OK", f"{ctype}")
                return ("BROKEN",
                        f"content-type is {ctype or 'unknown'!r}, not image/* "
                        f"(server returned a non-image, e.g. an HTML page — {len(blob)}+ bytes)")
        except urllib.error.HTTPError as e:
            return ("BROKEN", f"HTTP {e.code}")
        except ssl.SSLCertVerificationError:
            continue  # local trust-store can't verify — retry unverified, don't false-fail
        except urllib.error.URLError as e:
            if isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
                continue
            return ("BROKEN", f"connection failed ({e.reason})")
        except Exception as e:  # noqa: BLE001
            return ("BROKEN", f"{type(e).__name__}: {e}")
    return ("BROKEN", "connection failed (SSL verification failed even unverified)")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--url":
        urls = [a for a in argv[1:] if a != "--url"]
    else:
        try:
            html = open(argv[0], encoding="utf-8", errors="ignore").read()
        except OSError as e:
            print(f"cannot read {argv[0]}: {e}")
            return 2
        urls = extract_urls(html)

    if not urls:
        print("No image URLs found.")
        return 0

    broken, warn, ok = [], [], []
    for u in urls:
        status, detail = check(u)
        mark = {"OK": "OK  ", "WARN": "WARN", "BROKEN": "FAIL"}[status]
        print(f"[{mark}] {u}\n        {detail}")
        (ok if status == "OK" else warn if status == "WARN" else broken).append(u)

    print(f"\n{len(ok)} ok | {len(warn)} warn | {len(broken)} broken  (of {len(urls)})")
    if broken:
        print("GATE FAILED — remove or replace the broken URLs before saving to Folloze.")
        return 1
    if warn:
        print("Warnings present (e.g. base64) — review before saving.")
    print("Gate passed — every image loads as a real image.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
