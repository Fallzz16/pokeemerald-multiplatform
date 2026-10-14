#!/usr/bin/env python3
"""Create isolated Emerald Hybrid LAN test saves near the Oldale Cable Club.

QA-only fixtures: never import this generated data into a real player save.

Source is one *publicly provided* vanilla Emerald test save from the
PokemonBoxSaveEditor repository. No ROM data is included in this output.

This tool never modifies an existing local save. It verifies Git blob id,
flash-sector checksums, and all patched save sectors, then writes two 128 KiB
files with distinct trainer identities. Gameplay loading still needs QA.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/VitHuang/PokemonBoxSaveEditor/master/emerald.sav"
SOURCE_BLOB_SHA1 = "5907d26962edc655ba0f352dd7daeacef28763c8"
FLASH_SIZE = 128 * 1024
SECTOR = 4096
SIGNATURE = 0x08012025
SECTOR_DATA = 3968
# Emerald SaveBlock2 is 0xF2C long; SaveBlock1's first section is complete.
CHECKSUM_BYTES = {0: 0xF2C, 1: SECTOR_DATA}

# Map data taken from data/maps/map_groups.json and
# data/layouts/layouts.json of the current Emerald Hybrid repository.
# Oldale Town Pokemon Center 2F = group 2, map 3, layout 62.
CENTER_MAP = (2, 3)
CENTER_LAYOUT_ID = 62
CENTER_POS = (10, 4)  # facing the Direct Corner attendant at (10, 2)

def u16(b: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<H", b, off)[0]

def u32(b: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]

def checksum(data: bytes | bytearray, off: int, size: int) -> int:
    if size % 4:
        raise ValueError("size not aligned")
    v = sum(u32(data, off + p) for p in range(0, size, 4)) & 0xFFFFFFFF
    return ((v >> 16) + v) & 0xFFFF

def describe_save(data: bytes) -> list[dict]:
    if len(data) != FLASH_SIZE:
        raise ValueError(f"expected 131072 byte Emerald battery save, found {len(data)}")
    slots = []
    for slot_index in range(2):
        sectors = {}
        counters = set()
        for phys in range(slot_index * 14, (slot_index + 1) * 14):
            off = phys * SECTOR
            ident = u16(data, off + 4084)
            sign = u32(data, off + 4088)
            count = u32(data, off + 4092)
            if sign != SIGNATURE or ident >= 14 or ident in sectors:
                raise ValueError(f"invalid or duplicate flash sector: slot={slot_index}, physical={phys}, id={ident}")
            counters.add(count)
            sectors[ident] = phys
            if ident in CHECKSUM_BYTES:
                expected = checksum(data, off, CHECKSUM_BYTES[ident])
                got = u16(data, off + 4086)
                if got != expected:
                    raise ValueError(f"bad original checksum: sector id={ident}: {got:04x} != {expected:04x}")
        if sorted(sectors) != list(range(14)) or len(counters) != 1:
            raise ValueError(f"missing sectors / mismatched counters in slot {slot_index}")
        sb1 = sectors[1] * SECTOR
        sb2 = sectors[0] * SECTOR
        slots.append({
            "slot": slot_index, "sector_index": sectors,
            "counter": counters.pop(),
            "group": data[sb1 + 4], "map": data[sb1 + 5],
            "party_size": data[sb1 + 0x234],
            "trainer_id": u32(data, sb2 + 0x0A)
        })
    return slots

def patch_save(source: bytes, trainer_name: str, trainer_id: int) -> bytes:
    data = bytearray(source)
    slots = describe_save(data)
    for record in slots:
        sectors = record["sector_index"]
        sb1 = sectors[1] * SECTOR
        sb2 = sectors[0] * SECTOR

        # SaveBlock1: current tile, current map and layout; warpid=0xFF
        # means "use pos instead of warping to a specified event".
        struct.pack_into("<hh", data, sb1 + 0x00, *CENTER_POS)
        struct.pack_into("<BBB", data, sb1 + 0x04, *CENTER_MAP, 0xFF)
        struct.pack_into("<H", data, sb1 + 0x32, CENTER_LAYOUT_ID)
        # Update save-sector 1's footer checksum after changing the map.
        struct.pack_into("<H", data, sb1 + 4086, checksum(data, sb1, CHECKSUM_BYTES[1]))

        # SaveBlock2: give host and client distinct identities.
        # Gen III game's uppercase character table: 'A' = 0xBB.
        encoded = bytes(0xBB + ord(c) - ord("A") for c in trainer_name)
        if not trainer_name.isalpha() or not trainer_name.isupper() or len(encoded) > 7:
            raise ValueError("trainer name must be 1-7 uppercase ASCII letters")
        data[sb2:sb2 + 8] = (encoded + b"\xFF").ljust(8, b"\xFF")
        struct.pack_into("<I", data, sb2 + 0x0A, trainer_id)
        struct.pack_into("<H", data, sb2 + 4086, checksum(data, sb2, CHECKSUM_BYTES[0]))
    after = describe_save(data)
    for s in after:
        if (s["group"], s["map"]) != CENTER_MAP or not 1 <= s["party_size"] <= 6 or s["trainer_id"] != trainer_id:
            raise ValueError(f"failed verification for {trainer_name}: {s}")
    return bytes(data)

def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/lan-qa-saves")
    output.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "EmeraldHybridLAN-LocalQA/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(FLASH_SIZE + 1)

    blob_hash = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()
    if blob_hash != SOURCE_BLOB_SHA1:
        raise ValueError(f"the upstream save changed (blob {blob_hash}), refusing to use it")

    source_desc = describe_save(raw)
    if any(r["party_size"] < 2 or r["party_size"] > 6 for r in source_desc):
        raise ValueError(f"upstream save lacks an adequate battle party: {source_desc}")

    specs = [("HOST", 0x105A0001, "Host"), ("CLIENT", 0x105A0002, "Cliente")]
    manifests = []
    for name, trainer_id, directory in specs:
        data = patch_save(raw, name, trainer_id)
        target = output / directory / "pokeemerald.sav"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifests.append({
            "name": name, "trainer_id": f"{trainer_id:08X}",
            "path": str(target.relative_to(output)),
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "party_count": describe_save(data)[0]["party_size"]
        })

    guide = """SAVE DE TESTE — EMERALD HYBRID LAN
====================================
DOIS arquivos pokeemerald.sav de 128 KB, com nome/ID diferentes.
- Host/pokeemerald.sav  (treinador HOST)
- Cliente/pokeemerald.sav (treinador CLIENT)

Preparados para carregar no SEGUNDO ANDAR do Centro Pokemon de
Oldale Town, perto do balcao direito / Direct Corner.

INSTALACAO:
1. Feche as instancias do jogo.
2. Extraia cada copia completa do jogo Windows em uma pasta diferente.
3. Faca backup do seu pokeemerald.sav ORIGINAL (se houver).
4. Copie Host/pokeemerald.sav para a pasta do EXE do host.
5. Copie Cliente/pokeemerald.sav para a pasta do EXE do cliente.
6. Abra as duas instancias. O link vai ao Centro Pokemon, 2F.
7. Host: pokeemerald.exe --lan-log host.log --lan-host=45680
8. Client: pokeemerald.exe --lan-log cliente.log --lan-client=127.0.0.1:45680
9. Fale com a atendente do canto DIREITO, Direct Corner.
10. Teste Colosseum (batalha) e Trade Center (troca).

ATENCAO: saves de TESTE gerados de um save publico de referencia.
Checksums e estrutura validados; NAO foi confirmado boot/partida
em duas instancias reais. Caso a tela nao carregue a localizacao,
reporte o problema antes de usar saves principais. NAO compartilhe
esses dados como progressos oficiais ou saves seus.
O mundo compartilhado ainda nao esta implementado.
Fonte base: https://github.com/VitHuang/PokemonBoxSaveEditor/blob/master/emerald.sav
"""
    (output / "LEIA_PRIMEIRO.txt").write_text(guide, encoding="utf-8")
    (output / "MANIFESTO.json").write_text(json.dumps({
        "source_url": SOURCE_URL, "source_blob_sha1": blob_hash,
        "location": "OldaleTown_PokemonCenter_2F", "map": [2, 3],
        "position": list(CENTER_POS), "layout_id": CENTER_LAYOUT_ID,
        "saves": manifests
    }, indent=2), encoding="utf-8")
    print(json.dumps(manifests, indent=2))
    print("Ready:", output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
