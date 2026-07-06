#!/usr/bin/env python3
"""
update_products.py

Complète automatiquement products.json : pour chaque produit qui n'a pas encore
de titre / image / infos, va chercher ces informations directement sur la page
du produit (balises Open Graph), avec un service de secours (microlink.io) si
le site bloque la lecture directe.

Utilisation :
    pip install requests beautifulsoup4
    python update_products.py

Par défaut, le script cherche products.json dans le même dossier que lui.
Tu peux aussi préciser un chemin :
    python update_products.py chemin/vers/products.json
"""

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10
MICROLINK_URL = "https://api.microlink.io/"
MAX_DESCRIPTION_LENGTH = 90


def hostname_of(url: str) -> str:
    try:
        host = urlparse(url).hostname or url
        return host.replace("www.", "")
    except Exception:
        return url


def get_meta(soup: BeautifulSoup, *names: str) -> str | None:
    """Retourne le premier contenu trouvé parmi plusieurs balises meta possibles."""
    for name in names:
        tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def scrape_page(url: str) -> dict | None:
    """Essaie de lire directement la page du produit (balises Open Graph)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title = get_meta(soup, "og:title", "twitter:title")
        if not title and soup.title:
            title = soup.title.get_text(strip=True)

        image = get_meta(soup, "og:image", "twitter:image")
        publisher = get_meta(soup, "og:site_name") or hostname_of(url)
        description = get_meta(soup, "og:description", "description", "twitter:description")

        if not title and not image:
            return None  # rien d'exploitable, on tentera le service de secours

        return {
            "title": title or hostname_of(url),
            "image": image,
            "publisher": publisher,
            "description": description,
        }
    except Exception:
        return None


def scrape_via_microlink(url: str) -> dict | None:
    """Service de secours : utile quand un site bloque les requêtes directes."""
    try:
        resp = requests.get(MICROLINK_URL, params={"url": url}, timeout=TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "success":
            return None
        data = payload.get("data", {})
        image = data.get("image", {}).get("url") if data.get("image") else None
        return {
            "title": data.get("title") or hostname_of(url),
            "image": image,
            "publisher": data.get("publisher") or hostname_of(url),
            "description": data.get("description"),
        }
    except Exception:
        return None


def fetch_product_info(url: str) -> dict:
    info = scrape_page(url) or scrape_via_microlink(url)
    if not info:
        return {
            "title": hostname_of(url),
            "image": None,
            "publisher": hostname_of(url),
            "infos": [],
        }

    infos = []
    description = info.get("description")
    if description:
        description = description.strip()
        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH].rstrip() + "…"
        infos.append(description)

    return {
        "title": info["title"],
        "image": info.get("image"),
        "publisher": info.get("publisher"),
        "infos": infos,
    }


def needs_update(product: dict) -> bool:
    return bool(product.get("url")) and not (product.get("title") and product.get("image"))


def main():
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "products.json"

    if not json_path.exists():
        print(f"Fichier introuvable : {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        products = json.load(f)

    updated_count = 0

    for product in products:
        if not needs_update(product):
            continue

        url = product["url"]
        print(f"→ Récupération des infos pour : {url}")
        info = fetch_product_info(url)

        product["title"] = product.get("title") or info["title"]
        product["image"] = product.get("image") or info["image"]
        product["publisher"] = product.get("publisher") or info["publisher"]

        if not product.get("infos") and info["infos"]:
            product["infos"] = info["infos"]

        updated_count += 1
        time.sleep(1)  # petite pause pour rester poli avec les serveurs visités

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"\n{updated_count} produit(s) complété(s). Fichier mis à jour : {json_path}")


if __name__ == "__main__":
    main()
