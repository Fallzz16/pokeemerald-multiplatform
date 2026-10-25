#!/usr/bin/env python3
"""Generate a *review-required* PT-BR draft from pinned World sources.

This is never a replacement for human editorial review. The resulting entries
only join the game if all original symbols, control tokens, glyphs, and source
positions pass the same strict checks as hand-authored manifests.
"""
import argparse
from collections import Counter, defaultdict
import json
import re
import sys
import textwrap
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_ptbr_stage1 as pt

HEADER = re.compile(r"^([A-Za-z_]\w*)::?\s*$", re.M)
ASM_STR = re.compile(r'(?m)^\s*\.string\s+"((?:\\.|[^"\\])*)"\s*$')
GBA_BREAK = re.compile(r"\\[nlp]")
PLACEHOLDER = re.compile(r"(\{[^{}]+\})")
ENGLISH_LEFT = re.compile(r"\b(?:the|your|you|this|that|with|and|from|would|should)\b", re.I)
GLOSSARY = {
    "POKEMON": "POKEMON", "POKEDEX": "POKEDEX",
    "TRAINER": "TREINADOR", "TRAINERS": "TREINADORES",
    "GYM": "GINASIO", "GYMS": "GINASIOS",
    "BADGE": "INSIGNIA", "BADGES": "INSIGNIAS",
}
SAFE_PUNCTUATION = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": "'", "\u201d": "'",
    "\u2013": "-", "\u2014": "-", "\u2026": "...",
    "\u00a0": " ", "\u2022": "-", "\u00ab": "'", "\u00bb": "'",
})


def normalize(s):
    s = s.translate(SAFE_PUNCTUATION)
    s = s.replace("POKéMON", "POKEMON").replace("POKéDEX", "POKEDEX")
    s = s.replace("Pokémon", "Pokemon").replace("Pokédex", "Pokedex")
    s = "".join(x for x in unicodedata.normalize("NFKD", s)
                if not unicodedata.combining(x))
    return s


def get_original_labels(source):
    headers = list(HEADER.finditer(source))
    for i, hdr in enumerate(headers):
        until = headers[i + 1].start() if i + 1 < len(headers) else len(source)
        body = source[hdr.end():until]
        parts = ASM_STR.findall(body)
        if not parts or len(re.findall(r"(?m)^\s*\.string\b", body)) != len(parts):
            continue
        combined = "".join(parts)
        if not combined.endswith("$") or combined.count("$") != 1:
            continue
        yield hdr.group(1), combined


def translate_fragments(page, translator, cache):
    fragments = PLACEHOLDER.split(page.replace(r"\n", " ").replace(r"\l", " "))
    result = []
    for part in fragments:
        if not part:
            continue
        if PLACEHOLDER.fullmatch(part):
            result.append(part)
            continue
        cleaned = normalize(part)
        if not re.search("[A-Za-z]", cleaned):
            result.append(cleaned)
            continue
        if cleaned not in cache:
            cache[cleaned] = translator(cleaned)
        translated = normalize(cache[cleaned])
        for original, portuguese in GLOSSARY.items():
            translated = re.sub(r"\b" + original + r"\b",
                                portuguese, translated)
        # Named world entities, item names and move names in ALL CAPS
        # are not allowed to disappear in machine-generated proposals.
        protected = set(re.findall(r"\b[A-Z][A-Z0-9_']{2,}\b", cleaned))
        protected.difference_update(GLOSSARY)
        if any(not re.search(r"\b" + re.escape(word) + r"\b", translated)
               for word in protected):
            raise ValueError("named game term was modified")
        result.append(translated)
    return " ".join("".join(result).split())


def wrap_page(text):
    # Keep GBA control tokens atomic, and use scrolling for lines >= 3.
    lines = textwrap.wrap(text, width=31, break_long_words=False,
                          break_on_hyphens=False)
    if not lines:
        return ""
    if len(lines) > 12:
        raise ValueError("too many wrapped lines in page")
    return "".join(line + (r"\n" if i == 0 else r"\l")
                   for i, line in enumerate(lines[:-1])) + lines[-1]


def translate_label(old, translator, cache):
    if r"\"" in old or re.search(r"\\(?![nlp])", old):
        raise ValueError("unsupported source escape")
    pages = old[:-1].split(r"\p")
    out = []
    for page in pages:
        out.append(wrap_page(translate_fragments(page, translator, cache)))
    translated = r"\p".join(out) + "$"
    if not translated.isascii():
        raise ValueError("non-ASCII normalized translation")
    if not translated.endswith("$"):
        raise ValueError("lost terminator")
    old_visible = re.sub(r"\\[nlp]", " ", normalize(old[:-1]))
    new_visible = re.sub(r"\\[nlp]", " ", translated[:-1])
    if " ".join(old_visible.split()).casefold() == " ".join(new_visible.split()).casefold():
        raise ValueError("no translation")
    # Ignore long model generations that would damage ROM layout.
    if len(translated) > max(55, int(len(old) * 1.55)):
        raise ValueError("excessive expansion")
    if ENGLISH_LEFT.search(translated):
        raise ValueError("common English remained")
    return translated


def make_translator():
    import argostranslate.package
    import argostranslate.translate
    argostranslate.package.update_package_index()
    matches = [p for p in argostranslate.package.get_available_packages()
               if p.from_code == "en" and p.to_code == "pt"]
    if not matches:
        raise RuntimeError("Argos English-to-Portuguese package unavailable")
    package = sorted(matches, key=lambda p: str(p.package_version))[-1]
    argostranslate.package.install_from_path(package.download())

    def run(text):
        return argostranslate.translate.translate(text, "en", "pt")
    return run, str(package.package_version)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--minimum", type=int, default=5000)
    ap.add_argument("--maximum", type=int, default=5100)
    args = ap.parse_args()
    if args.minimum < 1 or args.maximum < args.minimum:
        ap.error("bad minimum or maximum")
    world = args.world.resolve()
    if not (world / "Makefile").exists():
        raise ValueError("World checkout missing")
    callback, model_version = make_translator()
    claimed = {key for file, data in pt.ASM_SECTIONS.items()
               for key in ((file, name) for name in data)}
    paths = list((world / "data/maps").glob("*/scripts.inc"))
    paths += list((world / "data/text").glob("*.inc"))
    paths = sorted(paths, key=lambda path: (
        0 if "Gym" in str(path) else
        1 if any(x in str(path) for x in ("Route", "Lab", "Rocket")) else 2,
        str(path)))
    selected = defaultdict(dict)
    rejected = Counter()
    cache = {}
    count = 0
    for path in paths:
        rel = str(path.relative_to(world))
        source = path.read_text(encoding="utf-8")
        for name, old in get_original_labels(source):
            if (rel, name) in claimed:
                continue
            try:
                translated = translate_label(old, callback, cache)
                pt.validate_translation(world, old, translated, name)
                # Exercise the real source replacement in preflight, not only
                # string validation. This remains a no-write check.
                pt.translate_asm(world, source, {name: [translated]}, rel)
            except (ValueError, KeyError, UnicodeError) as exc:
                rejected[str(exc).split(":")[0][:75]] += 1
                continue
            selected[rel][name] = [translated]
            count += 1
            if count % 200 == 0:
                print("PT-BR draft:", count, "accepted", flush=True)
            if count >= args.maximum:
                break
        if count >= args.maximum:
            break
    if count < args.minimum:
        raise RuntimeError("Only %d validated candidate texts, need %d" %
                           (count, args.minimum))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    shards = []
    number = 0
    batch = defaultdict(dict)
    batch_count = 0
    for rel, mapping in selected.items():
        for name, parts in mapping.items():
            batch[rel][name] = parts
            batch_count += 1
            if batch_count >= 250:
                number += 1
                filename = "ptbr_auto_review_%03d.json" % number
                (args.output_dir / filename).write_text(
                    json.dumps({"asm": dict(batch), "c": {}},
                               ensure_ascii=True, indent=2) + "\n")
                shards.append(filename)
                batch = defaultdict(dict)
                batch_count = 0
    if batch_count:
        number += 1
        filename = "ptbr_auto_review_%03d.json" % number
        (args.output_dir / filename).write_text(
            json.dumps({"asm": dict(batch), "c": {}},
                       ensure_ascii=True, indent=2) + "\n")
        shards.append(filename)
    metadata = {
        "source": "evilchinesefood/PKMN-World at pinned commit",
        "language": "pt-BR without accents, machine-assisted draft",
        "translation_model": "Argos en-pt %s" % model_version,
        "review_required": True,
        "gameplay_approved": False,
        "added_entries": count,
        "shards": shards,
        "rejected_reason_counts": dict(rejected),
    }
    (args.output_dir / "ptbr_auto_review_index.json").write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2) + "\n")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
