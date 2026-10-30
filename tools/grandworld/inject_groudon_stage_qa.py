#!/usr/bin/env python3
"""Inject 3 native mGBA-only WRAM staging assertions into Groudon QA."""
import argparse
from pathlib import Path
import sys

FINISH = "\n  F.finish()\nend)\n"
EXTRA = """
  local staged=F.r32(S.gGWGroudonStagedRequests)
  local overflow=F.r32(S.gGWGroudonStagingFallbacks)
  local vblank=F.r32(S.gGWGroudonRequestsInVBlank)
  F.L(string.format("GROUDON_STAGE staged=%d fallbacks=%d requests_in_vblank=%d",
    staged,overflow,vblank))
  F.check("Groudon frames genuinely staged in WRAM before VBlank",
    staged>=3,"staged requests="..staged)
  F.check("no VRAM BIOS fallback was necessary for single Groudon follower",
    overflow==0,"fallback="..overflow)
  F.check("Groudon decompression requests did not originate during VBlank",
    vblank==0,"during VBlank="..vblank)
"""


def inject(source):
    if source.count(FINISH)!=1 or source.count("__GROUDON_FNV_LIST__")!=0:
        raise ValueError("FAIL CLOSED: QA source format changed or hashes missing")
    if "GROUDON_STAGE staged=" in source:
        raise ValueError("FAIL CLOSED: staging QA already instrumented")
    return source.replace(FINISH,EXTRA+FINISH,1)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("qa",type=Path)
    args=p.parse_args()
    try:
        src=args.qa.read_text(encoding="utf-8")
        args.qa.write_text(inject(src),encoding="utf-8")
    except (ValueError,OSError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
