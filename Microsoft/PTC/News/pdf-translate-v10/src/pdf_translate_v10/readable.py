from __future__ import annotations

from .extract import raw_to_readable
from .models import LayoutLimit, ReadableTextState, TranslationInput, TranslationInputItem


def visual_units(text: str) -> float:
    total = 0.0
    previous_space = False
    for char in text:
        if char.isspace():
            total += 0.12 if previous_space else 0.28
            previous_space = True
        elif "가" <= char <= "힣":
            total += 1.0
            previous_space = False
        elif "\u4e00" <= char <= "\u9fff":
            total += 1.0
            previous_space = False
        elif char.isascii() and char.isalnum():
            total += 0.55
            previous_space = False
        elif char.isascii():
            total += 0.35
            previous_space = False
        else:
            total += 0.8
            previous_space = False
    return total


def convert_raw_to_readable(raw) -> ReadableTextState:
    return ReadableTextState(raw_to_readable(raw))


def build_translation_input(readable: ReadableTextState, terms) -> TranslationInput:
    items: list[TranslationInputItem] = []
    for item in readable.items:
        units = visual_units(item.source)
        font_size = item.layout.fontSize or 10.0
        limit = LayoutLimit(
            maxVisualUnits=max(units * 0.9, 1.0),
            maxHangulChars=max(int(units * 0.9), 1),
            sourceVisualUnits=units,
            spacingVisualUnits=item.layout.spacingVisualUnits or 0.0,
            fontSize=font_size,
            safetyRatio=0.9,
        )
        items.append(TranslationInputItem(item.id, item.source, limit))
    return TranslationInput(items, terms)