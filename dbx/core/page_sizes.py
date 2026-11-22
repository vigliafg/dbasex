"""Formati pagina condivisi da report ed etichette."""

from __future__ import annotations

PAGE_SIZES = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}


def page_dimensions(page_size: str, orientation: str = "portrait") -> tuple[float, float]:
    """Larghezza e altezza in millimetri, con orientamento applicato."""
    width, height = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
    if str(orientation).lower() == "landscape":
        width, height = height, width
    return width, height


__all__ = ["PAGE_SIZES", "page_dimensions"]
