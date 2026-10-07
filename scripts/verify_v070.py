#!/usr/bin/env python3
"""Static v0.7 audit; runs without Pillow or Nintendo donor files."""
from pathlib import Path
from hashlib import sha256
import ast

ROOT=Path(__file__).resolve().parents[1]
required={
    'tools/sprite_bridge.py':('def species_dex_numbers(', 'def apply_transaction(', 'MAX_DOWNLOAD = 2 * 1024 * 1024',
                              "raise SpriteError(f'{species}: not a confirmed Gen1-3 species", 'if not args.apply:',
                              "'before_sha256':digest(old)", "'after_sha256':digest(data)"),
    'scripts/test_sprite_bridge.py':('test_transaction_and_real_backup', 'test_oversize_visible_sprite_blocked',
                                    'test_palette_overflow_blocked', 'test_file_write_failure_rolls_back',
                                    'test_donor_missing_does_not_change_project'),
    'SPRITE_BRIDGE.bat':('tools\\sprite_bridge.py', '%*'),
    'SPRITE_BRIDGE_LEIA.md':('64', 'backup', 'Gen4'),
}
for name, tokens in required.items():
    content=(ROOT/name).read_text(encoding='utf-8')
    for token in tokens:
        if token not in content:
            raise AssertionError(f'{name} missing required guard: {token}')
for src in ('tools/sprite_bridge.py','scripts/test_sprite_bridge.py','scripts/verify_v070.py'):
    ast.parse((ROOT/src).read_text(encoding='utf-8'),filename=src)
# No Gen4 species or sprite assets are added by the v0.7 update itself.
assert not (ROOT/'graphics/pokemon/lucario').exists(), 'Unexpected Gen4 species asset present'
print('v0.7.0 STATIC preflight: PASS (source-only, no graphics applied)')
