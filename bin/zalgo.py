#!/usr/bin/env python3
"""Add bounded Unicode Zalgo marks to text on a scale from 1 to 100."""

import argparse
import math
import random
import sys
import unicodedata
from typing import Optional


MAX_INPUT_CHARS = 100_000

ABOVE = tuple(
    chr(code)
    for start, end in (
        (0x0300, 0x0315),
        (0x033D, 0x0344),
        (0x0346, 0x0346),
        (0x034A, 0x034C),
        (0x0350, 0x0352),
        (0x0357, 0x0357),
        (0x035B, 0x035B),
        (0x0363, 0x036F),
    )
    for code in range(start, end + 1)
)
MIDDLE = tuple(chr(code) for code in range(0x0334, 0x0339))
BELOW = tuple(
    chr(code)
    for start, end in (
        (0x0316, 0x0333),
        (0x0339, 0x033C),
        (0x0347, 0x0349),
        (0x034D, 0x034E),
        (0x0353, 0x0356),
        (0x0359, 0x035A),
    )
    for code in range(start, end + 1)
)
ZONES = (ABOVE, MIDDLE, BELOW)


class ZalgoError(ValueError):
    """Input cannot be transformed safely within the filter's bounds."""


def _eligible(character: str) -> bool:
    return (
        not character.isspace()
        and not unicodedata.combining(character)
        and not unicodedata.category(character).startswith("C")
    )


def _validate(text: str, scale: int) -> None:
    if isinstance(scale, bool) or not isinstance(scale, int) or not 1 <= scale <= 100:
        raise ZalgoError("scale must be an integer from 1 to 100")
    if len(text) > MAX_INPUT_CHARS:
        raise ZalgoError(f"input exceeds {MAX_INPUT_CHARS:,} characters")
    for character in text:
        category = unicodedata.category(character)
        if category.startswith("C") and character not in "\n\r\t":
            raise ZalgoError(
                f"input contains unsupported control or format character U+{ord(character):04X}"
            )


def zalgo(text: str, scale: int, seed: Optional[int] = None) -> str:
    """Return text decorated with combining marks at the requested intensity."""
    _validate(text, scale)
    rng = random.Random(seed)
    eligible_positions = [
        index for index, character in enumerate(text) if _eligible(character)
    ]
    if not eligible_positions:
        return text

    coverage = math.sqrt(scale / 100)
    maximum_marks = 1 + round((scale - 1) * 15 / 99)
    minimum_marks = max(1, maximum_marks // 2)
    forced_position = rng.choice(eligible_positions)

    output = []
    for index, character in enumerate(text):
        output.append(character)
        if not _eligible(character):
            continue
        if index != forced_position and rng.random() >= coverage:
            continue
        mark_count = rng.randint(minimum_marks, maximum_marks)
        for _ in range(mark_count):
            zone = rng.choice(ZONES)
            output.append(rng.choice(zone))
    return "".join(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", help="text to transform; omit to read stdin")
    parser.add_argument(
        "-s", "--scale", type=int, default=25, help="Zalgo intensity from 1 to 100"
    )
    parser.add_argument("--seed", type=int, help="repeatable random seed")
    args = parser.parse_args()

    text = args.text if args.text is not None else sys.stdin.read(MAX_INPUT_CHARS + 1)
    try:
        transformed = zalgo(text, args.scale, args.seed)
    except ZalgoError as error:
        parser.error(str(error))

    sys.stdout.write(transformed)
    if sys.stdout.isatty() and not transformed.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
