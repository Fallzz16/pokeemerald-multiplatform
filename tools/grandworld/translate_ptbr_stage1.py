#!/usr/bin/env python3
"""PT-BR stage 1: deterministic, fail-closed localization of pinned World sources.

No save data, item/move/ability/species names, IDs or existing original branch
are modified. Apply in a fresh isolated World checkout after M8 adapters.
"""
import argparse
from collections import Counter
import json
import re
import unicodedata
from pathlib import Path

# One deliberately reviewable entry per original string: upstream drift fails closed.
MAIN_MENU = {
    "gText_MainMenuNewGame": ("New Game", "Novo Jogo"),
    "gText_MainMenuContinue": ("Continue", "Continuar"),
    "gText_MainMenuOption": ("Options", "Ajustes"),
    "gText_MainMenuMysteryGift": ("MYSTERY GIFT", "PRES. MISTER."),
    "gText_MainMenuMysteryGift2": ("MYSTERY GIFT", "PRES. MISTER."),
    "gText_MainMenuMysteryEvents": ("MYSTERY EVENTS", "EVENTOS MIST."),
    "gText_ContinueMenuPlayer": ("PLAYER", "JOGADOR"),
    "gText_ContinueMenuTime": ("TIME", "TEMPO"),
    "gText_ContinueMenuBadges": ("BADGES", "INSÍGNIAS"),
    "gText_SaveFileCorrupted": (
        r"The save file is corrupted. The\nprevious save file will be loaded.",
        r"O jogo salvo foi danificado.\nO backup será carregado."),
    "gText_SaveFileErased": (
        r"The save file has been erased\ndue to corruption or damage.",
        r"O jogo salvo foi apagado\npor falha nos dados."),
    "gText_WirelessNotConnected": (
        r"The Wireless Adapter is not\nconnected.",
        r"O adaptador sem fio\nestá desconectado."),
}

CORE_TEXT = {
    "gText_Time": ("TIME", "TEMPO"),
    "gText_Badges": ("BADGES", "INSÍGNIAS"),
    "gText_Next": ("{A_BUTTON}NEXT", "{A_BUTTON}SEGUIR"),
    "gText_NextBack": ("{A_BUTTON}NEXT {B_BUTTON}BACK", "{A_BUTTON}SEGUIR {B_BUTTON}VOLTAR"),
    "gText_Boy": ("BOY", "MENINO"),
    "gText_Girl": ("GIRL", "MENINA"),
    "gText_ThisIsAPokemon": (
        r"This is what we call a “POKéMON.”{PAUSE 96}\p",
        r"Este é um POKéMON!{PAUSE 96}\p"),
    "gText_SearchingPleaseWait": (r"Searching…\nPlease wait.", r"Buscando…\nAguarde."),
    "gText_SearchCompleted": ("Search completed.", "Busca concluída."),
    "gText_NoMatchingPkmnWereFound": (
        "No matching POKéMON were found.", "Nenhum POKéMON encontrado."),
    "gText_SearchForPkmnBasedOnParameters": (
        r"Search for POKéMON based on\nselected parameters.",
        r"Busque POKéMON usando\nos filtros escolhidos."),
    "gText_ReturnToPokedex": ("Return to the POKéDEX.", "Voltar à POKéDEX."),
    "gText_DexHoennTitle": ("REGION DEX", "DEX REGIONAL"),
    "gText_DexNatTitle": ("NATIONAL DEX", "DEX NACIONAL"),
    "gText_DexSortNumericalTitle": ("NUMERICAL MODE", "ORDEM NUMÉRICA"),
    "gText_DexSortAtoZTitle": ("A TO Z MODE", "ORDEM A A Z"),
    "gText_DexSortHeaviestTitle": ("HEAVIEST MODE", "MAIS PESADOS"),
    "gText_DexSortLightestTitle": ("LIGHTEST MODE", "MAIS LEVES"),
    "gText_DexSortTallestTitle": ("TALLEST MODE", "MAIS ALTOS"),
    "gText_DexSortSmallestTitle": ("SMALLEST MODE", "MAIS BAIXOS"),
    "gText_DexSearchColorRed": ("RED", "VERMELHO"),
    "gText_DexSearchColorBlue": ("BLUE", "AZUL"),
    "gText_DexSearchColorYellow": ("YELLOW", "AMARELO"),
    "gText_DexSearchColorGreen": ("GREEN", "VERDE"),
    "gText_DexSearchColorBlack": ("BLACK", "PRETO"),
    "gText_DexSearchColorBrown": ("BROWN", "MARROM"),
    "gText_DexSearchColorPurple": ("PURPLE", "ROXO"),
    "gText_DexSearchColorGray": ("GRAY", "CINZA"),
    "gText_DexSearchColorWhite": ("WHITE", "BRANCO"),
    "gText_DexSearchColorPink": ("PINK", "ROSA"),
    "gText_DexHoennDescription": ("your region's POKéDEX", "POKéDEX da sua terra"),
    "gText_DexNatDescription": ("National edition POKéDEX", "POKéDEX de todo o mundo"),
    "gText_DexSearchTypeNone": ("NONE", "NENHUM"),
    "gText_WelcomeToHOF": ("Welcome to the HALL OF FAME!", "Bem-vindo ao HALL DA FAMA!"),
    "gText_LeagueChamp": (
        r"LEAGUE CHAMPION!\nCONGRATULATIONS!",
        r"VENCEU A LIGA!\nPARABÉNS!"),
    "gText_Name": ("NAME", "NOME"),
    "gText_ConfirmStarterChoice": (
        "Do you choose this POKéMON?", "Quer escolher este POKéMON?"),
    "gText_FlyToWhere": ("FLY to where?", "Voar para onde?"),
    "gMenuText_Use": ("Use", "Usar"),
    "gMenuText_Toss": ("Toss", "Descartar"),
    "gMenuText_Register": ("Register", "Registrar"),
    "gMenuText_Give": ("Give", "Dar"),
    "gMenuText_Confirm": ("Confirm", "Confirmar"),
    "gText_Cancel": ("Cancel", "Cancelar"),
    "gText_Cancel2": ("Cancel", "Cancelar"),
    "gText_None": ("NONE", "NENHUM"),
    "gText_GoBackPrevMenu": (
        r"Go back to the\nprevious menu.", r"Voltar ao menu\nanterior."),
    "gText_WhatWouldYouLike": ("What would you like to do?", "O que deseja fazer?"),
    "gMenuText_Give2": ("Give", "Dar"),
    "gText_CloseBag": ("Close Bag", "Fechar Bolsa"),
    "gText_NoPokemon": (r"There is no\nPOKéMON.", r"Sem POKéMON."),
    "gText_TossHowManyVar1s": (
        r"Toss out how many\n{STR_VAR_1}?", r"Descartar quantos\n{STR_VAR_1}?"),
    "gText_ReturnToVar1": (r"Return to\n{STR_VAR_1}.", r"Voltar para\n{STR_VAR_1}."),
    "gText_ShopBuy": ("Buy", "Comprar"),
    "gText_ShopSell": ("Sell", "Vender"),
    "gText_ShopQuit": ("Quit", "Sair"),
    "gText_UseOnWhichPokemon": ("Use on which POKéMON?", "Usar em qual POKéMON?"),
    "gText_NoPokemonForBattle": ("No POKéMON for battle!", "Sem POKéMON para lutar!"),
    "gText_NotEnoughHp": ("Not enough HP…", "HP insuficiente…"),
    "gText_SaveCompleted": ("Save completed.", "Jogo salvo."),
    "gText_SaveFailed": ("Save failed…", "Falha ao salvar…"),
    "gText_Yes": ("Yes", "Sim"),
    "gText_Yes2": ("Yes", "Sim"),
    "gText_Yes3": ("Yes", "Sim"),
    "gText_TimeColon": ("Time:", "Tempo:"),
    "gText_Confirm2": ("Confirm", "Confirmar"),
    "gText_Confirm3": ("Confirm", "Confirmar"),
    "gText_Cancel3": ("Cancel", "Cancelar"),
    "gText_Cancel4": ("Cancel", "Cancelar"),
    "gText_Cancel5": ("Cancel", "Cancelar"),
}

# Original opening, written as independent short PT-BR dialogue rather than a
# byte-for-byte port. The control tokens and name variables must be kept.
BIRCH = {
    "gText_Birch_Welcome": [
        r"Oi! Desculpe a demora!\p",
        r"Bem-vindo ao mundo POKéMON!\p",
        r"Sou o PROF. BIRCH.\p",
        r"Estudo os POKéMON\ne seus mistérios.\p", "$",
    ],
    "gText_Birch_Pokemon": [r"Este é um POKéMON!\p", "$"],
    "gText_Birch_MainSpeech": [
        r"Neste mundo, os POKéMON vivem\npor toda parte.\p",
        r"Alguns fazem amizade\ncom as pessoas.\p",
        r"Outros treinam e lutam\nao nosso lado.\p",
        r"Mas ainda temos muito\na descobrir sobre eles.\p",
        r"Por isso, eu os estudo\ntodos os dias!\p", "$",
    ],
    "gText_Birch_AndYouAre": ["E você, quem é?$"],
    "gText_Birch_BoyOrGirl": [r"Você é um menino?\nOu uma menina?$"],
    "gText_Birch_WhatsYourName": [r"Legal!\nQual é seu nome?$"],
    "gText_Birch_SoItsPlayer": ["{PLAYER}{KUN}, certo?$"],
    "gText_Birch_YourePlayer": [
        r"Ah, entendi!\p",
        r"Você é {PLAYER}{KUN}.\nVai morar em LITTLEROOT.\p", "$",
    ],
    "gText_Birch_AreYouReady": [
        r"Preparado para a aventura?\p",
        r"Explore o mundo e faça\ngrandes amizades!\p",
        r"Quando puder, visite\nmeu LAB. POKéMON!\p", "$",
    ],
}

SAVE = {
    "gText_ConfirmSave": ["Quer salvar o jogo?$"],
    "gText_AlreadySavedFile": [
        r"Já existe um jogo salvo.\n",
        "Deseja sobrescrever?$",
    ],
    "gText_SavingDontTurnOff": [
        r"SALVANDO…\n", "MANTENHA O CONSOLE LIGADO.$",
    ],
    "gText_PlayerSavedGame": ["{PLAYER} salvou o jogo.$"],
    "gText_DifferentSaveFile": [
        r"CUIDADO!\p",
        r"Já existe outro jogo salvo.\p",
        r"Se continuar, o progresso\ne os POKéMON desse jogo",
        r"\lsomem para sempre.\p",
        r"Quer mesmo sobrescrever\no jogo salvo?$",
    ],
    "gText_SaveError": [
        r"Erro ao salvar.\p",
        r"Verifique a memória\ndo cartucho.$",
    ],
    "gText_SavingDontTurnOffPower": [
        r"SALVANDO…\n", "MANTENHA O CONSOLE LIGADO.$",
    ],
}

C_SECTIONS = {
    "src/main_menu.c": MAIN_MENU,
    "src/strings.c": CORE_TEXT,
}
ASM_SECTIONS = {
    "data/text/birch_speech.inc": BIRCH,
    "data/text/save.inc": SAVE,
}

# Expanded text batches are owned by this same fail-closed translator.
# Explicit originals in JSON prevent accidental replacements after upstream drift.
for file_name in ("ptbr_extra_core.json", "ptbr_extra_events.json", "ptbr_extra_world.json", "ptbr_extra_battle.json", "ptbr_extra_services2.json", "ptbr_extra_regions2.json", "ptbr_extra_story2.json", "ptbr_extra_labs3.json", "ptbr_extra_gyms3.json", "ptbr_extra_routes4.json", "ptbr_extra_gyms4.json", "ptbr_extra_dewford5.json", "ptbr_extra_routes5.json", "ptbr_extra_route110_6.json", "ptbr_extra_route111_6.json", "ptbr_extra_route112_6.json", "ptbr_extra_hoenn_routes6.json", "ptbr_extra_johto_routes6.json", "ptbr_extra_hoenn_routes7.json"):
    batch_path = Path(__file__).with_name(file_name)
    if batch_path.is_file():
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        for rel, data in batch.get("c", {}).items():
            target = C_SECTIONS.setdefault(rel, {})
            for label, pair in data.items():
                if label in target:
                    raise ValueError(f"duplicate localization label: {label}")
                target[label] = tuple(pair)
        for rel, data in batch.get("asm", {}).items():
            target = ASM_SECTIONS.setdefault(rel, {})
            for label, parts in data.items():
                if label in target:
                    raise ValueError(f"duplicate localization label: {label}")
                target[label] = parts

TOKEN = re.compile(r"\{[^{}]+\}")
# Keep source strings untouched, but normalize every NEW Portuguese line to ASCII.
# Names of species/moves/items/abilities and runtime identifiers are not modified.
CUSTOM_CHARACTER_MAP = ("ã", "õ", "Ã", "Õ", "ç", "Ç")


def plain_ptbr(value):
    value = (value.replace("POKéMON", "POKEMON")
                  .replace("POKéDEX", "POKEDEX")
                  .replace("Pokémon", "Pokemon")
                  .replace("Pokédex", "Pokedex")
                  .replace("…", "...")
                  .replace("“", "'").replace("”", "'"))
    value = "".join(c for c in unicodedata.normalize("NFKD", value)
                    if not unicodedata.combining(c))
    if any(ord(c) >= 128 for c in value):
        raise ValueError("PT-BR translation contains non-ASCII characters: " + repr(value))
    return value


def validate_glyphs(world, text):
    charmap = (world / "charmap.txt").read_text(encoding="utf-8")
    latin = charmap.split("@ Hiragana", 1)[0]
    glyphs = set(re.findall(r"^'([^'\\]{1})'\s*=", latin, re.M))
    if not glyphs:
        raise ValueError("could not parse Latin charmap")
    # Strip named placeholders/control sequences and GBA text escape sequences.
    text = TOKEN.sub("", text)
    text = re.sub(r"\\[npl]", "", text)
    missing = set(text) - glyphs
    if missing:
        raise ValueError("unsupported PT-BR glyph(s): " + repr(sorted(missing)))


def validate_translation(world, old, new, label):
    if Counter(TOKEN.findall(old)) != Counter(TOKEN.findall(new)):
        raise ValueError(f"{label}: game placeholder changed")
    for value in (old, new):
        if re.search(r"\\(?![npl])", value):
            raise ValueError(f"{label}: unknown text escape")
    validate_glyphs(world, new)


def translate_c(world, source, replacements, path):
    count = 0
    for symbol, (old, new) in replacements.items():
        new = plain_ptbr(new)
        validate_translation(world, old, new, symbol)
        pattern = (r"(?m)^([^\n]*\b" + re.escape(symbol)
                   + r"\[\]\s*=\s*_\(\")(" + re.escape(old) + r")"
                   + r"(\"\);[^\n]*$)")
        matches = list(re.finditer(pattern, source))
        if len(matches) != 1:
            raise ValueError(f"{path}::{symbol}: expected 1 exact source, found {len(matches)}")
        match = matches[0]
        source = source[:match.start(2)] + new + source[match.end(2):]
        count += 1
    return source, count


def translate_asm(world, source, entries, path):
    count = 0
    for label, parts in entries.items():
        pattern = r"(?ms)^(" + re.escape(label) + r"::?\n)(.*?)(?=^[A-Za-z_][\w]*::?|\Z)"
        found = list(re.finditer(pattern, source))
        if len(found) != 1:
            raise ValueError(f"{path}::{label}: expected 1 label, found {len(found)}")
        match = found[0]
        original = match.group(2)
        original_parts = re.findall(r'(?m)^\s*\.string\s+"((?:\\.|[^"\\])*)"\s*$', original)
        if not original_parts or len(re.findall(r"(?m)^\s*\.string\b", original)) != len(original_parts):
            raise ValueError(f"{path}::{label}: unexpected ASM text format")
        old = "".join(original_parts)
        parts = [plain_ptbr(part) for part in parts]
        new = "".join(parts)
        if not old.endswith("$") or not new.endswith("$"):
            raise ValueError(f"{path}::{label}: terminal $ lost")
        validate_translation(world, old, new, label)
        for part in parts:
            if '"' in part:
                raise ValueError(f"{path}::{label}: literal quote not escaped")
        new_lines = "".join('\t.string "' + part + '"\n' for part in parts)
        source = source[:match.start(2)] + new_lines + ("\n" if match.end(2) < len(source) else "") + source[match.end(2):]
        count += 1
    return source, count


def plan(world):
    world = Path(world)
    if not (world / "Makefile").is_file():
        raise ValueError("World checkout/Makefile missing")
    changes = {}
    by_file = {}
    for relative, mapping in C_SECTIONS.items():
        path = world / relative
        old = path.read_text(encoding="utf-8")
        new, count = translate_c(world, old, mapping, relative)
        changes[path] = (old, new)
        by_file[relative] = count
    for relative, mapping in ASM_SECTIONS.items():
        path = world / relative
        old = path.read_text(encoding="utf-8")
        new, count = translate_asm(world, old, mapping, relative)
        changes[path] = (old, new)
        by_file[relative] = count
    return changes, by_file


def run(world, write=False):
    world = Path(world)
    changes, by_file = plan(world)
    # All source edits are validated before the first file is modified.
    if write:
        for path, (_, new) in changes.items():
            path.write_text(new, encoding="utf-8")
    return {
        "mode": "applied" if write else "preflight",
        "locale": "pt-BR",
        "target": "complete Portuguese-only ROM, staged",
        "translation_entries": sum(by_file.values()),
        "by_file": by_file,
        "pokemon_names_translated": False,
        "move_names_translated": False,
        "ability_names_translated": False,
        "item_names_translated": False,
        "save_format_modified": False,
        "accent_tilde_font_complete": False,
        "translated_text_ascii_only": True,
        "full_text_review_complete": False,
        "gameplay_verified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = run(args.world, args.apply)
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
