#!/usr/bin/env python3
"""Append native GBA VBlank stress scenarios to existing Groudon follower QA.

The 9 original visual checks + 3 original timer checks execute first.
Stress modes 1,2,3 then repeat the same compressed frame 2/3/4 times
inside the actual VBlank sprite-copy queue without changing the final
graphics bytes. This is specifically a DECODE LOAD test, not simulation
of three other visible Pokémon.
"""
import argparse
from pathlib import Path
import sys

END="  F.finish()\nend)\n"
EXTRA="""  -- Diagnostic-only: each mode repeats the SAME native 2KiB frame
  -- 2, 3 or 4 times in the SAME ProcessSpriteCopyRequests call.
  -- No extra visible sprites are created; do not advertise this as such.
  local modes={}
  local stressGood=true
  local stressHasFrame=false
  local directions={"Down","Left","Right","Up","Down","Right","Left","Down",
                    "Up","Left","Down","Right","Up","Down","Right","Left"}
  for mode=1,3 do
    F.w8(S.gGWStressExtraCopies,mode)
    F.idle(25)
    local valid=0
    for i=1,#directions do
      F.step(directions[i]);F.idle(16)
      if F.reportCrash("vblank_stress_"..mode.."_"..i) then break end
      local ok,_,hash=snapshot("vblank-stress-"..mode.."-"..i)
      if ok then valid=valid+1;stressHasFrame=true else stressGood=false end
    end
    local base=mode*4
    local n=F.r32(S.gGWStressSamples+base)
    local peak=F.r32(S.gGWStressPeakBatchCycles+base)
    local over=F.r32(S.gGWStressOverBudgetBatches+base)
    local crossed=F.r32(S.gGWStressVblankCrossings+base)
    modes[mode]={n=n,peak=peak,over=over,crossed=crossed,valid=valid}
    F.L(string.format("GROUDON_STRESS mode=%d copies=%d samples=%d peak_batch_cycles=%d over_budget=%d crossed_vblank=%d pixel_samples=%d",
      mode,mode+1,n,peak,over,crossed,valid))
  end
  F.w8(S.gGWStressExtraCopies,0)
  local baselineN=F.r32(S.gGWStressSamples)
  local baselinePeak=F.r32(S.gGWStressPeakBatchCycles)
  local maxBatch=F.r32(S.gGWPeakMeasuredBatchCycles)
  local maxComp=F.r32(S.gGWPeakCompressedInOneBatch)
  local maxRaw=F.r32(S.gGWPeakNormalInOneBatch)
  F.L(string.format("GROUDON_BATCH baseline_samples=%d baseline_peak=%d max_batch_cycles=%d max_lz_copies=%d max_normal_copies=%d",
    baselineN,baselinePeak,maxBatch,maxComp,maxRaw))
  F.check("each experimental VBlank decode load level actually ran",
    modes[1].n>=3 and modes[2].n>=3 and modes[3].n>=3)
  F.check("GPU pixels match original frames after all stressed copy loads",
    stressGood and stressHasFrame and modes[1].valid>=4 and modes[2].valid>=4 and modes[3].valid>=4)
  F.check("real ARM batch CPU cost grows across two, three and four decodes",
    modes[1].peak>0 and modes[2].peak>modes[1].peak and modes[3].peak>modes[2].peak)
  F.check("two and three copies fit isolated VBlank CPU copy interval",
    modes[1].peak<83776 and modes[2].peak<83776)
  F.check("four 64x64 LZ10 copies detect a potential VBlank CPU overload",
    modes[3].peak>=83776 and modes[3].over>=1)
  F.check("GBA timer sampling remained uncontended under VBlank stress",
    F.r32(S.gGWLZTimerConflicts)==0)
  F.check("native sprite GPU stress does not crash the real ARM/GBA game",
    not F.reportCrash("vblank_stress_done"))
"""


def inject(qa):
    if qa.count(END)!=1 or "__GROUDON_FNV_LIST__" in qa:
        raise ValueError("FAIL CLOSED: Groudon QA is missing pinned 12-check source")
    if "GROUDON_STRESS mode=" in qa:
        raise ValueError("FAIL CLOSED: duplicate staging QA injection")
    if "GROUDON_CPU samples=" not in qa:
        raise ValueError("FAIL CLOSED: real timer QA not present")
    return qa.replace(END,EXTRA+END,1)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("qa",type=Path)
    args=p.parse_args()
    try:
        s=args.qa.read_text(encoding="utf-8")
        args.qa.write_text(inject(s),encoding="utf-8")
    except (OSError,ValueError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
