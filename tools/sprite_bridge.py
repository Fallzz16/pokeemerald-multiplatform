#!/usr/bin/env python3
"""Emerald Sprite Bridge v0.7: lossless, transactional Gen1-3 donor sprite import.

Examples:
 python tools/sprite_bridge.py --source platinum --species pikachu gardevoir
 python tools/sprite_bridge.py --source heartgold --species pikachu --apply
 python tools/sprite_bridge.py --source ruby --species abra,kadabra --donor-root C:/pokeruby --apply

Without --apply, everything is fetched and verified but the game is untouched.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from PIL import Image
except ImportError as e:
    raise SystemExit('Pillow required only for sprite imports: python -m pip install Pillow') from e

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'platinum': ('pret/pokeplatinum', 'main'),
    'heartgold': ('pret/pokeheartgold', 'master'),
    'ruby': ('pret/pokeruby', 'master'),
}
MAX_DOWNLOAD = 2 * 1024 * 1024
IMAGE_FILES = ('front.png', 'back.png', 'anim_front.png', 'normal.pal', 'shiny.pal')
SPECIAL_FORMS = frozenset(('castform', 'unown', 'spinda', 'deoxys'))

class SpriteError(Exception):
    pass

def pixels(image: Image.Image):
    """Pillow 12.3+ accessor without the deprecated getdata() warning."""
    if hasattr(image, 'get_flattened_data'):
        return image.get_flattened_data()
    return image.getdata()

def digest(blob: bytes) -> str:
    return sha256(blob).hexdigest()

def species_dex_numbers(root: Path) -> dict[str, int]:
    """Use the NATIONAL Pokédex, not Emerald's internal species IDs.

    The internal Gen3 range has padding for Old Unown and is not a Pokédex
    number (e.g. Ralts is SPECIES 392 but National Dex #280).
    """
    header = (root/'include/constants/pokedex.h').read_text(encoding='utf-8')
    block = header.split('// National Pokédex order', 1)[1].split('// Hoenn Pokédex order', 1)[0]
    species = [name.lower() for name in re.findall(r'^\s*NATIONAL_DEX_([A-Z0-9_]+),',block,re.M)]
    if not species or species[0] != 'none' or len(species) < 387:
        raise SpriteError('National Pokédex constants were not recognized; import blocked')
    # Only the first 386 standard National IDs; reject Old Unown placeholders.
    ids = {name: num for num,name in enumerate(species[:387]) if 1<=num<=386}
    present = {name.lower() for name in re.findall(r'^#define SPECIES_([A-Z0-9_]+)\s+\d+$',
                  (root/'include/constants/species.h').read_text(encoding='utf-8'),re.M)}
    return {name:num for name,num in ids.items() if name in present}

def donor_relative_paths(source: str, species: str, dexnum: int, gender: str) -> tuple[str,str,str|None,str|None]:
    if source == 'platinum':
        root = f'res/pokemon/{species}'
        return (f'{root}/{gender}_front.png',f'{root}/{gender}_back.png',f'{root}/normal.pal',f'{root}/shiny.pal')
    if source == 'heartgold':
        root = f'files/poketool/pokegra/pokegra/{dexnum:04d}/{gender}'
        return (f'{root}/front.png', f'{root}/back.png', None, None)
    root = f'graphics/pokemon/{species}'
    return (f'{root}/front.png', f'{root}/back.png', f'{root}/normal.pal', f'{root}/shiny.pal')

def fetch_blob(source: str, rel: str, donor_root: Path|None) -> bytes:
    if donor_root is not None:
        path = donor_root/rel
        if not path.is_file():
            raise SpriteError(f'Donor file not found: {path}')
        if path.stat().st_size > MAX_DOWNLOAD:
            raise SpriteError(f'Donor asset too large: {rel}')
        return path.read_bytes()
    repo, branch = SOURCES[source]
    url = f'https://raw.githubusercontent.com/{repo}/{branch}/{rel}'
    try:
        with urlopen(Request(url, headers={'User-Agent':'Emerald-SpriteBridge-v0.7'}),timeout=20) as response:
            payload = response.read(MAX_DOWNLOAD+1)
    except (OSError, URLError) as exc:
        raise SpriteError(f'Could not download {url}: {exc}') from exc
    if len(payload)>MAX_DOWNLOAD:
        raise SpriteError(f'Exceeded 2MB limit for {rel}')
    return payload

def parse_jasc(data: bytes, name: str) -> list[tuple[int,int,int]]:
    try:
        lines = data.decode('ascii').replace('\r','').splitlines()
        if lines[0].strip()!='JASC-PAL' or lines[1].strip()!='0100' or int(lines[2])!=16:
            raise ValueError('invalid JASC-PAL header')
        colors=[tuple(map(int, line.split())) for line in lines[3:19]]
        if len(colors)!=16 or any(len(x)!=3 or any(not 0<=v<=255 for v in x) for x in colors):
            raise ValueError('invalid RGB palette')
        return colors
    except (ValueError, IndexError, UnicodeDecodeError) as exc:
        raise SpriteError(f'Invalid donor palette {name}: {exc}') from exc

def rgba_sprite(data: bytes, name: str) -> tuple[Image.Image, dict]:
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != 'PNG':
                raise SpriteError(f'{name} is not PNG')
            # Force decoding now. No resizing or antialiasing is ever performed.
            image.load()
            rgba = image.convert('RGBA')
    except (OSError, ValueError) as exc:
        raise SpriteError(f'PNG decode failed {name}: {exc}') from exc
    if not 16 <= rgba.width <= 128 or not 16 <= rgba.height <= 128:
        raise SpriteError(f'{name}: dimensions {rgba.size} unsupported (16..128px)')
    alpha = [a for *_,a in pixels(rgba)]
    if any(0<a<255 for a in alpha):
        raise SpriteError(f'{name}: semitransparent pixels not safe for 4bpp import')
    if all(a==255 for a in alpha):
        # Older donor PNGs have an opaque uniform border instead of transparency.
        corners=[rgba.getpixel((0,0)),rgba.getpixel((rgba.width-1,0)),
                 rgba.getpixel((0,rgba.height-1)),rgba.getpixel((rgba.width-1,rgba.height-1))]
        if len(set(corners))!=1:
            raise SpriteError(f'{name}: opaque PNG without uniform corner background')
        bg=corners[0][:3]
        rgba.putdata([(r,g,b,0 if (r,g,b)==bg else 255) for r,g,b,a in pixels(rgba)])
    bounds = rgba.getbbox()
    if bounds is None:
        raise SpriteError(f'{name}: sprite is fully transparent')
    x0,y0,x1,y1=bounds
    if x1-x0>64 or y1-y0>64:
        raise SpriteError(f'{name}: visible sprite {x1-x0}x{y1-y0} exceeds 64x64. '
                          'Pixel-perfect import refused: no scaling or cropping of opaque pixels.')
    # Convert to GBA 64x64 with no resampling; center horizontally, bottom align.
    cropped=rgba.crop(bounds)
    output=Image.new('RGBA',(64,64),(0,0,0,0))
    output.paste(cropped,((64-cropped.width)//2,64-cropped.height))
    return output,{'input_size':list(rgba.size),'visible_size':[x1-x0,y1-y0],
                   'padded_to':[64,64],'scaled':False}

def palette_for(front: Image.Image, back: Image.Image, normal_src: list|None, shiny_src: list|None):
    # Both sprites must share a single 16-color indexed GBA palette.
    colors={}
    for image in (front,back):
        for r,g,b,a in pixels(image):
            if a==0:
                continue
            pixel=(r,g,b)
            if pixel not in colors:
                colors[pixel]=len(colors)+1
    if len(colors)>15:
        raise SpriteError(f'Combined front/back requires {len(colors)} opaque colors; '
                          'GBA permits 15 + transparency. Quantization is disabled to preserve exact colors.')
    ordered=[(0,0,0)]+list(colors)
    ordered+=([(0,0,0)]*(16-len(ordered)))
    shiny=list(ordered)
    shiny_mapped=0
    if normal_src and shiny_src:
        for color,index in colors.items():
            try:
                orig_index=normal_src.index(color)
            except ValueError:
                # PNG may contain RGB values not directly listed in donor palette;
                # never guess/recolor silently.
                continue
            shiny[index]=shiny_src[orig_index]
            shiny_mapped+=1
    return colors, ordered, shiny, shiny_mapped

def indexed_png(image: Image.Image, color_indices: dict) -> bytes:
    target=Image.new('P',(64,64),0)
    normal=[0,0,0]*16
    for color,index in color_indices.items():
        normal[index*3:index*3+3]=list(color)
    target.putpalette(normal)
    indices=[color_indices[(r,g,b)] if a else 0 for r,g,b,a in pixels(image)]
    target.putdata(indices)
    target.info['transparency']=0
    out=BytesIO()
    target.save(out,format='PNG',optimize=True)
    return out.getvalue()

def jasc(colors: list[tuple[int,int,int]]) -> bytes:
    return ('JASC-PAL\r\n0100\r\n16\r\n'+'\r\n'.join(f'{r} {g} {b}' for r,g,b in colors)+'\r\n').encode('ascii')

def prepare_species(root: Path, source: str, species: str, gender: str, dexnum: int,
                    donor_root: Path|None) -> tuple[dict[str,bytes],dict]:
    rels=donor_relative_paths(source,species,dexnum,gender)
    front_data=fetch_blob(source,rels[0],donor_root)
    back_data=fetch_blob(source,rels[1],donor_root)
    front,front_meta=rgba_sprite(front_data, f'{species}/front')
    back,back_meta=rgba_sprite(back_data, f'{species}/back')
    normal=shiny=None
    if rels[2]:
        normal=parse_jasc(fetch_blob(source,rels[2],donor_root),rels[2])
        shiny=parse_jasc(fetch_blob(source,rels[3],donor_root),rels[3])
    indices,pal,shiny_pal,shiny_mapped=palette_for(front,back,normal,shiny)
    front_bytes=indexed_png(front,indices)
    back_bytes=indexed_png(back,indices)
    # Emerald anim_front is exactly two 64x64 frames. A donor 1-frame sprite
    # is represented as two identical frames rather than inventing animation.
    anim=Image.new('P',(64,128),0)
    frame=Image.open(BytesIO(front_bytes))
    anim.putpalette(frame.getpalette())
    anim.paste(frame,(0,0))
    anim.paste(frame,(0,64))
    anim.info['transparency']=0
    anim_buf=BytesIO()
    anim.save(anim_buf,'PNG',optimize=True)
    content={'front.png':front_bytes,'back.png':back_bytes,'anim_front.png':anim_buf.getvalue(),
             'normal.pal':jasc(pal),'shiny.pal':jasc(shiny_pal)}
    report={'species':species,'dex_number':dexnum,'source':source,'gender':gender,
            'source_paths':[rels[0],rels[1]],'front':front_meta,'back':back_meta,
            'colors':len(indices),'shiny_color_matches':shiny_mapped,
            'shiny_palette_fallback': 'identical-to-normal' if not shiny_mapped else
                'unmatched-donor-colors-unchanged',
            'animation':'2 identical frames (donor static front)'}
    return content,report

def _write_atomic(path: Path, data: bytes):
    with tempfile.NamedTemporaryFile(prefix='.sprite-bridge-',dir=path.parent,delete=False) as stream:
        tmp=Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    os.replace(tmp,path)

def apply_transaction(root: Path, prepared: list[tuple[str,dict[str,bytes],dict]],
                      backup_dir: Path) -> Path:
    if backup_dir.exists():
        raise SpriteError(f'Backup path exists; not overwriting: {backup_dir}')
    backup_dir.mkdir(parents=True)
    original={}
    manifest=[]
    changed=[]
    try:
        for species, payload, meta in prepared:
            target=root/'graphics/pokemon'/species
            for name,data in payload.items():
                path=target/name
                if not path.is_file():
                    raise SpriteError(f'Original file missing: {path}')
                old=path.read_bytes()
                original[path]=old
                backup=backup_dir/species/name
                backup.parent.mkdir(parents=True,exist_ok=True)
                backup.write_bytes(old)
                manifest.append({'path':str(path.relative_to(root)).replace('\\','/'),
                                 'before_sha256':digest(old),'after_sha256':digest(data)})
        # Backups/manifest fully persisted before changing any sprite files.
        (backup_dir/'manifest.json').write_text(json.dumps({'files':manifest,'species':[m[2] for m in prepared]},
                                                           indent=2),encoding='utf-8')
        for species,payload,meta in prepared:
            for name,data in payload.items():
                path=root/'graphics/pokemon'/species/name
                _write_atomic(path,data)
                changed.append(path)
        return backup_dir
    except Exception:
        for path in reversed(changed):
            _write_atomic(path,original[path])
        raise

def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='Gen1–3 DS/Ruby sprite import, pixel-perfect / safe batch with backup')
    p.add_argument('--source',required=True,choices=sorted(SOURCES))
    p.add_argument('--species',nargs='+',required=True,help='Known Emerald species, space/comma separated')
    p.add_argument('--gender',choices=('male','female'),default='male')
    p.add_argument('--donor-root',type=Path,help='Optional local extracted donor repo (offline support)')
    p.add_argument('--repo',type=Path,default=ROOT,help='Emerald source root; default: this project')
    p.add_argument('--apply',action='store_true',help='Explicitly import into current source; creates backup')
    p.add_argument('--backup-dir',type=Path,help='Optional new backup path (must not exist)')
    p.add_argument('--report',type=Path,help='Write preflight manifest JSON (outside repository preferred)')
    args=p.parse_args(argv)
    root=args.repo.resolve()
    ids=species_dex_numbers(root)
    targets=list(dict.fromkeys(s.strip().lower().replace('-','_') for raw in args.species for s in raw.split(',') if s.strip()))
    if not targets:
        raise SpriteError('No species selected')
    if len(targets)>50:
        raise SpriteError('Maximum 50 species per batch for safe rollback and network usage')
    for species in targets:
        if not re.fullmatch('[a-z0-9_]+',species) or species not in ids:
            raise SpriteError(f'{species}: not a confirmed Gen1-3 species in this Emerald (new species engine NOT installed)')
        if species in SPECIAL_FORMS:
            raise SpriteError(f'{species}: special forms or dynamic sprites require a dedicated importer')
        if not (root/'graphics/pokemon'/species/'front.png').is_file():
            raise SpriteError(f'{species}: standard front.png missing; special forms must be handled separately')
    donor_root=args.donor_root.resolve() if args.donor_root else None
    if donor_root and not donor_root.is_dir():
        raise SpriteError('Donor folder does not exist: '+str(donor_root))
    prepared=[]
    for species in targets:
        print(f'Checking {species} ({args.source})...')
        content,meta=prepare_species(root,args.source,species,args.gender,ids[species],donor_root)
        prepared.append((species,content,meta))
    report={'status':'preflight_passed','source':args.source,'count':len(prepared),
            'apply_requested':args.apply,'pixel_resampling':False,
            'details':[meta for _,_,meta in prepared]}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'Preflight PASS: {len(prepared)} species, no scaling/quantization, full rollback-ready payload.')
    if not args.apply:
        print('DRY RUN: project unchanged. Add --apply to import in one batch with backups.')
        return 0
    backup=args.backup_dir or (root.parent/(root.name+'_sprite_backups')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output=apply_transaction(root,prepared,backup.resolve())
    print(f'APPLIED: {len(prepared)} species; original assets backed up at {output}')
    print('Next step: compile and visually check normal/shiny, battle front/back and animations.')
    return 0

if __name__=='__main__':
    try:
        sys.exit(main())
    except SpriteError as exc:
        print('SPRITE BRIDGE BLOCKED: '+str(exc),file=sys.stderr)
        sys.exit(2)
