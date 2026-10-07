#!/usr/bin/env python3
"""Offline executable regressions for the Sprite Bridge (no internet/SDK needed)."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import shutil
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import sprite_bridge as sb
from PIL import Image

class SpriteBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'Emerald'
        for sub in ('include/constants','graphics/pokemon/pikachu','graphics/pokemon/ralts'):
            (self.root/sub).mkdir(parents=True,exist_ok=True)
        for name in ('species.h','pokedex.h'):
            shutil.copy2(ROOT/'include/constants'/name,self.root/'include/constants'/name)
        self.donor=Path(self.tmp.name)/'pokeruby'
        for species in ('pikachu','ralts'):
            dest=self.root/'graphics/pokemon'/species
            source=ROOT/'graphics/pokemon'/species
            for name in sb.IMAGE_FILES:
                shutil.copy2(source/name,dest/name)
            donor=self.donor/'graphics/pokemon'/species
            donor.mkdir(parents=True)
            for name in ('front.png','back.png','normal.pal','shiny.pal'):
                shutil.copy2(source/name,donor/name)
    def params(self, species='pikachu'):
        return ['--source','ruby','--species',species,'--repo',str(self.root),'--donor-root',str(self.donor)]
    def snapshot(self):
        return {p.relative_to(self.root).as_posix():sb.digest(p.read_bytes())
                for p in (self.root/'graphics/pokemon').rglob('*') if p.is_file()}
    def test_national_dex_numbers(self):
        ids=sb.species_dex_numbers(self.root)
        self.assertEqual(ids['pikachu'],25)
        self.assertEqual(ids['ralts'],280)
        self.assertEqual(ids['gardevoir'],282)
        self.assertEqual(ids['deoxys'],386)
        self.assertEqual(len(ids),386)
        self.assertNotIn('old_unown_b',ids)
    def test_paths_all_three_donors(self):
        self.assertEqual(sb.donor_relative_paths('heartgold','lucario',448,'male')[0],
                         'files/poketool/pokegra/pokegra/0448/male/front.png')
        self.assertEqual(sb.donor_relative_paths('platinum','gardevoir',282,'female')[0],
                         'res/pokemon/gardevoir/female_front.png')
    def test_preflight_does_not_change_project(self):
        before=self.snapshot()
        self.assertEqual(sb.main(self.params('pikachu,ralts')),0)
        self.assertEqual(before,self.snapshot())
    def test_transaction_and_real_backup(self):
        before=self.snapshot()
        path=Path(self.tmp.name)/'backups'
        self.assertEqual(sb.main(self.params('pikachu,ralts')+['--apply','--backup-dir',str(path)]),0)
        entries=json.loads((path/'manifest.json').read_text())['files']
        self.assertEqual(len(entries),10)
        for entry in entries:
            target=self.root/entry['path']
            original=path/Path(entry['path']).relative_to('graphics/pokemon')
            self.assertEqual(sb.digest(target.read_bytes()),entry['after_sha256'])
            self.assertEqual(sb.digest(original.read_bytes()),entry['before_sha256'])
            self.assertEqual(entry['before_sha256'],before[entry['path']])
        pic=Image.open(self.root/'graphics/pokemon/pikachu/front.png')
        animation=Image.open(self.root/'graphics/pokemon/pikachu/anim_front.png')
        self.assertEqual(pic.size,(64,64))
        self.assertEqual(animation.size,(64,128))
        self.assertEqual(list(sb.pixels(pic)),list(sb.pixels(animation.crop((0,0,64,64)))))
        self.assertEqual(list(sb.pixels(pic)),list(sb.pixels(animation.crop((0,64,64,128)))))
        with self.assertRaises(sb.SpriteError):
            sb.main(self.params('pikachu')+['--apply','--backup-dir',str(path)])
    def test_oversize_visible_sprite_blocked(self):
        dest=self.donor/'graphics/pokemon/pikachu/front.png'
        img=Image.new('RGB',(80,80),(255,255,255))
        for y in range(80):
            for x in range(80):
                if 1 <= x < 79 and 1 <= y < 79:
                    img.putpixel((x,y),(0,0,0))
        img.save(dest)
        before=self.snapshot()
        with self.assertRaisesRegex(sb.SpriteError,'exceeds 64x64'):
            sb.main(self.params('pikachu')+['--apply'])
        self.assertEqual(before,self.snapshot())
    def test_palette_overflow_blocked(self):
        dest=self.donor/'graphics/pokemon/pikachu/front.png'
        im=Image.new('RGBA',(64,64),(0,0,0,0))
        for i in range(16):
            im.putpixel((i,0),(i*13+1,0,0,255))
        im.save(dest)
        before=self.snapshot()
        with self.assertRaisesRegex(sb.SpriteError,r'15 \+ transparency'):
            sb.main(self.params('pikachu')+['--apply'])
        self.assertEqual(before,self.snapshot())
    def test_dont_import_unknown_species(self):
        with self.assertRaisesRegex(sb.SpriteError,'not a confirmed Gen1-3'):
            sb.main(self.params('lucario')+['--apply'])
    def test_file_write_failure_rolls_back(self):
        before=self.snapshot()
        real=sb._write_atomic
        n=[0]
        def fail_second(path,data):
            n[0]+=1
            if n[0]==2:
                raise OSError('simulate sudden disk error')
            return real(path,data)
        with patch.object(sb,'_write_atomic',side_effect=fail_second):
            with self.assertRaisesRegex(OSError,'simulat'):
                sb.main(self.params('pikachu')+['--apply','--backup-dir',str(Path(self.tmp.name)/'rollback')])
        self.assertEqual(before,self.snapshot())
    def test_special_forms_blocked(self):
        with self.assertRaisesRegex(sb.SpriteError,'special forms or dynamic'):
            sb.main(self.params('spinda')+['--apply'])
    def test_donor_missing_does_not_change_project(self):
        (self.donor/'graphics/pokemon/ralts/back.png').unlink()
        before=self.snapshot()
        with self.assertRaisesRegex(sb.SpriteError,'Donor file not found'):
            sb.main(self.params('pikachu,ralts')+['--apply'])
        self.assertEqual(before,self.snapshot())

if __name__ == '__main__':
    unittest.main(verbosity=2)
