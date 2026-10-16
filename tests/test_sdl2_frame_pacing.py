"""Static regression of SDL pending-frame busy spin; neither ROM nor saves touched."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SDLFrameGuardTests(unittest.TestCase):
    def test_loop_yields_on_unavailable_frame(self):
        source=(ROOT/"src/platform/sdl2.c").read_text(encoding="utf-8")
        start=source.index("while (accumulator >= dt)")
        end=source.index("SDL_RenderPresent(sdlRenderer);",start)
        body=source[start:end]
        self.assertIn("if (SDL_AtomicGet(&isFrameAvailable))",body)
        self.assertRegex(body,r"else\s*\{\s*/\* EHL8_FRAME_WAIT:[\s\S]*?\*/\s*break;\s*\}")

    def test_exact_inverse_audit(self):
        from scripts.verify_v080_profile_patch import strip_v080_profile_patch
        source=(ROOT/"src/platform/sdl2.c").read_text(encoding="utf-8")
        original=strip_v080_profile_patch(source)
        self.assertNotIn("EHL8_FRAME_WAIT",original)
        self.assertIn("while (accumulator >= dt)",original)

if __name__=="__main__":
    unittest.main()
