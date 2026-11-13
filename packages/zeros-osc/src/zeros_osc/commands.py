"""ZerOS OSC commands for the FLX S24.

Every command in this module comes from ``docs/02-flx-osc-referenz.md``.
Nothing else may be added here. Commands with status "offen" are not included.

All builders return the address in the form "everything in the path, no
arguments", e.g. ``/zeros/cue/go/10/2``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

PLAYBACK_MIN = 0
PLAYBACK_MAX = 96  # FLX S24: 97 playbacks, 0 is the master playback
LEVEL_MIN = 0
LEVEL_MAX = 100

WILDCARD_CHARS = frozenset("*?[]{}")


class ZerosValueError(ValueError):
    """A value or address does not fit the reference."""


class Status(Enum):
    """Status levels as defined in the reference."""

    BELEGT = "belegt"  # documented in the ZerOS manual
    FORUM = "Forum"  # only mentioned in the vendor forum -> "ungetestet"

    @property
    def untested(self) -> bool:
        return self is Status.FORUM


# --- value normalisers ---------------------------------------------------------
# Each takes a user value (int, float, Decimal or str) and returns the path
# segment as a string, or raises ZerosValueError with a German message
# (these messages are shown to operators by flxctl).


def _to_decimal(value: object, what: str) -> Decimal:
    if isinstance(value, bool):
        raise ZerosValueError(f"{what}: {value!r} ist keine Zahl")
    if isinstance(value, int | Decimal):
        number = Decimal(value)
    elif isinstance(value, float | str):
        try:
            number = Decimal(str(value).strip())
        except InvalidOperation:
            raise ZerosValueError(f"{what}: {value!r} ist keine Zahl") from None
    else:
        raise ZerosValueError(f"{what}: {value!r} ist keine Zahl")
    if not number.is_finite():
        raise ZerosValueError(f"{what}: {value!r} ist keine endliche Zahl")
    return number


def _format_decimal(number: Decimal) -> str:
    """Plain notation without exponent and without trailing zeros (2.50 -> 2.5, 3.0 -> 3)."""
    text = format(number.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _to_int(value: object, what: str) -> int:
    number = _to_decimal(value, what)
    if number != number.to_integral_value():
        raise ZerosValueError(f"{what}: {value!r} muss eine ganze Zahl sein")
    return int(number)


def norm_playback(value: object) -> str:
    number = _to_int(value, "Playback")
    if not PLAYBACK_MIN <= number <= PLAYBACK_MAX:
        raise ZerosValueError(
            f"Playback: {number} liegt außerhalb von {PLAYBACK_MIN} bis {PLAYBACK_MAX}"
        )
    return str(number)


def norm_cue(value: object) -> str:
    """Cue number > 0; point cues such as 2.5 are allowed."""
    number = _to_decimal(value, "Cue")
    if number <= 0:
        raise ZerosValueError(f"Cue: {value!r} muss größer als 0 sein")
    return _format_decimal(number)


def norm_macro(value: object) -> str:
    # The reference gives no range; macro numbers start at 1 (example: /zeros/macro/1).
    number = _to_int(value, "Makro")
    if number < 1:
        raise ZerosValueError(f"Makro: {number} muss 1 oder größer sein")
    return str(number)


def norm_level(value: object) -> str:
    number = _to_int(value, "Level")
    if not LEVEL_MIN <= number <= LEVEL_MAX:
        raise ZerosValueError(f"Level: {number} liegt außerhalb von {LEVEL_MIN} bis {LEVEL_MAX}")
    return str(number)


def norm_fade(value: object) -> str:
    """Fade time in seconds, >= 0, decimals allowed (0 forces a hard cut)."""
    number = _to_decimal(value, "Fade-Zeit")
    if number < 0:
        raise ZerosValueError(f"Fade-Zeit: {value!r} darf nicht negativ sein")
    return _format_decimal(number)


_BLACKOUT_WORDS = {"1": "1", "0": "0", "on": "1", "off": "0", "true": "1", "false": "0"}


def norm_blackout(value: object) -> str:
    """Blackout on/off. Accepts 1/0, on/off, true/false and bool; always sends 1 or 0."""
    if isinstance(value, bool):
        return "1" if value else "0"
    key = str(value).strip().lower()
    if key in _BLACKOUT_WORDS:
        return _BLACKOUT_WORDS[key]
    raise ZerosValueError(f"Blackout: {value!r} muss 1/0, on/off oder true/false sein")


# --- command table -------------------------------------------------------------


@dataclass(frozen=True)
class Param:
    name: str
    normalise: Callable[[object], str]
    help: str


PLAYBACK = Param("playback", norm_playback, f"Playback-Nummer {PLAYBACK_MIN} bis {PLAYBACK_MAX}")
CUE = Param("cue", norm_cue, "Cue-Nummer größer 0, Punkt-Cues wie 2.5 erlaubt")
MACRO = Param("number", norm_macro, "Makro-Nummer ab 1")
LEVEL = Param("level", norm_level, f"Level in Prozent {LEVEL_MIN} bis {LEVEL_MAX}")
FADE = Param("fade", norm_fade, "Fade-Zeit in Sekunden, zum Beispiel 2 oder 2.5")
BLACKOUT = Param("value", norm_blackout, "1/on = an, 0/off = aus")


@dataclass(frozen=True)
class Command:
    id: str
    summary: str  # German, as in the reference ("Funktion")
    prefix: tuple[str, ...]  # fixed path segments
    params: tuple[Param, ...]  # required path parameters
    optional: tuple[Param, ...]  # optional trailing path parameters
    status: Status
    example: str  # example address from the reference
    cli: tuple[str, ...]  # flxctl subcommand path

    def build(self, *values: object) -> str:
        """Validate values and return the address."""
        lo = len(self.params)
        hi = lo + len(self.optional)
        given = list(values)
        # Trailing None means "optional parameter not given".
        while len(given) > lo and given[-1] is None:
            given.pop()
        if not lo <= len(given) <= hi:
            raise ZerosValueError(f"{self.id}: erwartet {lo} bis {hi} Werte, bekam {len(given)}")
        specs = (self.params + self.optional)[: len(given)]
        segments = [spec.normalise(value) for spec, value in zip(specs, given, strict=True)]
        return "/" + "/".join(self.prefix + tuple(segments))

    @property
    def pattern(self) -> str:
        parts = "/" + "/".join(self.prefix)
        parts += "".join(f"/<{p.name}>" for p in self.params)
        parts += "".join(f"[/<{p.name}>]" for p in self.optional)
        return parts


COMMANDS: dict[str, Command] = {
    c.id: c
    for c in (
        Command(
            "cue_go",
            "Cue auf einem Playback starten",
            ("zeros", "cue", "go"),
            (PLAYBACK, CUE),
            (),
            Status.BELEGT,
            "/zeros/cue/go/1/5",
            ("cue", "go"),
        ),
        Command(
            "cue_go_current",
            "Cue im gerade angezeigten Playback starten",
            ("zeros", "cue", "go"),
            (CUE,),
            (),
            Status.FORUM,
            "/zeros/cue/go/4",
            ("cue", "go-current"),
        ),
        Command(
            "cue_go_next",
            "nächsten Cue starten",
            ("zeros", "cue", "go"),
            (),
            (),
            Status.FORUM,
            "/zeros/cue/go",
            ("cue", "go-next"),
        ),
        Command(
            "macro",
            "Makro auslösen",
            ("zeros", "macro"),
            (MACRO,),
            (),
            Status.FORUM,
            "/zeros/macro/1",
            ("macro",),
        ),
        Command(
            "cue_pause",
            "Cue anhalten",
            ("zeros", "cue", "pause"),
            (PLAYBACK,),
            (),
            Status.FORUM,
            "/zeros/cue/pause/1",
            ("cue", "pause"),
        ),
        Command(
            "cue_next",
            "nächsten Cue vorwählen",
            ("zeros", "cue", "next"),
            (PLAYBACK, CUE),
            (),
            Status.FORUM,
            "/zeros/cue/next/1/6",
            ("cue", "next"),
        ),
        Command(
            "playback_go",
            "Playback starten",
            ("zeros", "playback", "go"),
            (PLAYBACK,),
            (),
            Status.FORUM,
            "/zeros/playback/go/1",
            ("playback", "go"),
        ),
        Command(
            "playback_pause",
            "Playback anhalten",
            ("zeros", "playback", "pause"),
            (PLAYBACK,),
            (),
            Status.FORUM,
            "/zeros/playback/pause/1",
            ("playback", "pause"),
        ),
        Command(
            "playback_level",
            "Playback-Level setzen, optional mit Fade-Zeit",
            ("zeros", "playback", "level"),
            (PLAYBACK, LEVEL),
            (FADE,),
            Status.FORUM,
            "/zeros/playback/level/1/100",
            ("playback", "level"),
        ),
        Command(
            "playback_release",
            "Playback freigeben",
            ("zeros", "playback", "release"),
            (PLAYBACK,),
            (),
            Status.FORUM,
            "/zeros/playback/release/1",
            ("playback", "release"),
        ),
        Command(
            "playback_view",
            "Playback anzeigen",
            ("zeros", "playback", "view"),
            (PLAYBACK,),
            (),
            Status.FORUM,
            "/zeros/playback/view/1",
            ("playback", "view"),
        ),
        Command(
            "grand_master",
            "Grand Master setzen, optional mit Fade-Zeit",
            ("zeros", "grandmaster"),
            (LEVEL,),
            (FADE,),
            Status.FORUM,
            "/zeros/grandmaster/100",
            ("grandmaster",),
        ),
        Command(
            "blackout",
            "Blackout schalten",
            ("zeros", "blackout"),
            (BLACKOUT,),
            (),
            Status.FORUM,
            "/zeros/blackout/1",
            ("blackout",),
        ),
    )
}


# --- public builder functions (one per reference command) ---------------------


def cue_go(playback: object, cue: object) -> str:
    """Start a cue on a playback: /zeros/cue/go/<playback>/<cue> (belegt)."""
    return COMMANDS["cue_go"].build(playback, cue)


def cue_go_current(cue: object) -> str:
    """Start a cue on the currently viewed playback: /zeros/cue/go/<cue> (Forum, untested)."""
    return COMMANDS["cue_go_current"].build(cue)


def cue_go_next() -> str:
    """Start the next cue: /zeros/cue/go (Forum, untested)."""
    return COMMANDS["cue_go_next"].build()


def macro(number: object) -> str:
    """Fire a macro: /zeros/macro/<number> (Forum, untested)."""
    return COMMANDS["macro"].build(number)


def cue_pause(playback: object) -> str:
    """Pause a cue: /zeros/cue/pause/<playback> (Forum, untested)."""
    return COMMANDS["cue_pause"].build(playback)


def cue_next(playback: object, cue: object) -> str:
    """Preselect the next cue: /zeros/cue/next/<playback>/<cue> (Forum, untested)."""
    return COMMANDS["cue_next"].build(playback, cue)


def playback_go(playback: object) -> str:
    """Go on a playback: /zeros/playback/go/<playback> (Forum, untested)."""
    return COMMANDS["playback_go"].build(playback)


def playback_pause(playback: object) -> str:
    """Pause a playback: /zeros/playback/pause/<playback> (Forum, untested)."""
    return COMMANDS["playback_pause"].build(playback)


def playback_level(playback: object, level: object, fade: object | None = None) -> str:
    """Set a playback level: /zeros/playback/level/<playback>/<level>[/<fade>] (Forum)."""
    return COMMANDS["playback_level"].build(playback, level, fade)


def playback_release(playback: object) -> str:
    """Release a playback: /zeros/playback/release/<playback> (Forum, untested)."""
    return COMMANDS["playback_release"].build(playback)


def playback_view(playback: object) -> str:
    """View a playback: /zeros/playback/view/<playback> (Forum, untested)."""
    return COMMANDS["playback_view"].build(playback)


def grand_master(level: object, fade: object | None = None) -> str:
    """Set the grand master: /zeros/grandmaster/<level>[/<fade>] (Forum, untested)."""
    return COMMANDS["grand_master"].build(level, fade)


def blackout(value: object) -> str:
    """Switch blackout: /zeros/blackout/<1|0> (Forum, untested)."""
    return COMMANDS["blackout"].build(value)


# --- address matching ----------------------------------------------------------


@dataclass(frozen=True)
class Match:
    command: Command
    values: tuple[str, ...]


def match_address(address: str) -> Match:
    """Return the reference command an address belongs to, or raise ZerosValueError.

    The address must be in the form this repo sends: everything in the path,
    no wildcards. Values are checked with the same rules as the builders, and
    the address must already be in normalised form (e.g. ``/zeros/cue/go/1/05``
    is rejected because the builder would send ``/zeros/cue/go/1/5``).
    """
    if not isinstance(address, str) or not address.startswith("/"):
        raise ZerosValueError(f"Adresse {address!r} muss mit / beginnen")
    if WILDCARD_CHARS & set(address):
        raise ZerosValueError(f"Adresse {address!r} enthält Wildcards; ZerOS verwirft sie")
    segments = tuple(address[1:].split("/"))
    if "" in segments or any(s != s.strip() for s in segments):
        raise ZerosValueError(f"Adresse {address!r} hat leere Segmente oder Leerzeichen")

    errors: list[str] = []
    for command in COMMANDS.values():
        n = len(command.prefix)
        if segments[:n] != command.prefix:
            continue
        values = segments[n:]
        lo = len(command.params)
        if not lo <= len(values) <= lo + len(command.optional):
            continue
        try:
            built = command.build(*values)
        except ZerosValueError as exc:
            errors.append(f"{command.id}: {exc}")
            continue
        if built != address:
            errors.append(f"{command.id}: Schreibweise abweichend, erwartet {built}")
            continue
        return Match(command, values)
    if errors:
        raise ZerosValueError(f"Adresse {address}: " + "; ".join(errors))
    raise ZerosValueError(f"Adresse {address} passt zu keinem Befehl der Referenz")


def address_warnings(match: Match) -> list[str]:
    """Known caveats from the reference for a matched address (German)."""
    notes: list[str] = []
    if match.command.status.untested:
        notes.append(f"{match.command.id} ist ungetestet (Status Forum)")
    if match.command.id == "cue_go" and match.values[0] == "0":
        notes.append(
            "Playback 0 (Master): laut Forum auf einem FLX S48 ignoriert, in Teststufe 2 prüfen"
        )
    return notes
