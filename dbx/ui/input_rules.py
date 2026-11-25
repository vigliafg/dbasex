"""Regole di forma dell'input: maiuscole e maschere (piano validazione).

Il modulo è puro: non importa Qt e non conosce widget. La stessa logica è usata
da griglia, nuovo record e Form Runtime tramite `input_editors`.
"""

from __future__ import annotations

CASE_MODES = ("", "upper", "lower", "title", "sentence")
MASK_CHARS = frozenset("9Aa ")


class InputRules:
    """Trasformazioni e controlli di forma sul testo digitato."""

    @staticmethod
    def apply_case(text: str, mode: str) -> str:
        """Applica la modalità maiuscole; una modalità ignota lascia il testo."""
        text = str(text or "")
        if not text or not mode:
            return text
        if mode == "upper":
            return text.upper()
        if mode == "lower":
            return text.lower()
        if mode == "title":
            return text.title()
        if mode == "sentence":
            chars = list(text)
            for index, char in enumerate(chars):
                if char.isalpha():
                    chars[index] = char.upper()
                    break
            return "".join(chars)
        return text

    @staticmethod
    def mask_slots(mask: str) -> dict[int, str]:
        """Mappa posizione → carattere della maschera."""
        return {index: char for index, char in enumerate(str(mask or ""))}

    @staticmethod
    def accepts(mask_char: str, char: str) -> bool:
        """Il carattere è ammesso nella posizione della maschera?"""
        if mask_char == "9":
            return char.isdigit()
        if mask_char in ("A", "a"):
            return char.isalpha()
        return char == mask_char

    @staticmethod
    def normalize_char(mask_char: str, char: str) -> str:
        """Normalizza il carattere secondo lo slot (``A`` maiuscolo, ``a`` minuscolo)."""
        if mask_char == "A":
            return char.upper()
        if mask_char == "a":
            return char.lower()
        return char

    @staticmethod
    def check(mask: str, text: str) -> str:
        """Verifica il testo contro la maschera e lo restituisce normalizzato.

        Il testo può essere parziale (utile durante la digitazione); solleva
        ``ValueError`` se eccede la maschera o se un carattere non è ammesso.
        """
        mask = str(mask or "")
        text = str(text or "")
        if not mask:
            return text
        if len(text) > len(mask):
            raise ValueError("Il testo supera la lunghezza della maschera")
        result: list[str] = []
        for index, char in enumerate(text):
            slot = mask[index]
            if not InputRules.accepts(slot, char):
                raise ValueError(
                    f"Carattere non ammesso alla posizione {index + 1}: {char!r}"
                )
            result.append(InputRules.normalize_char(slot, char))
        return "".join(result)

    @staticmethod
    def fits(mask: str, text: str) -> bool:
        try:
            InputRules.check(mask, text)
        except ValueError:
            return False
        return True

    @staticmethod
    def placeholder(mask: str) -> str:
        """Segnaposto leggibile per un campo con maschera."""
        return "".join(
            "0" if char == "9" else "A" if char == "A" else "a" if char == "a" else char
            for char in str(mask or "")
        )

    @staticmethod
    def shape(field, text: str) -> str:
        """Applica maiuscole e maschera a un valore digitato."""
        if field is None:
            return str(text or "")
        result = InputRules.apply_case(text, getattr(field, "case_mode", ""))
        mask = str(getattr(field, "mask", "") or "")
        if mask:
            try:
                result = InputRules.check(mask, result)
            except ValueError:
                # L'editor blocca già i caratteri non ammessi; qui non si perde
                # il testo eventualmente parziale.
                pass
        return result

    @staticmethod
    def is_complete(field, text: str) -> bool:
        """Il valore ha raggiunto la lunghezza della maschera o del campo."""
        if field is None:
            return False
        mask = str(getattr(field, "mask", "") or "")
        text = str(text or "")
        if mask:
            return len(text) >= len(mask)
        size = int(getattr(field, "size", 0) or 0)
        return bool(size and len(text) >= size)


__all__ = ["CASE_MODES", "MASK_CHARS", "InputRules"]
