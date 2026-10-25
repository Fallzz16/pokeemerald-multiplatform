"""Normalize ARM-only assembly *comments* emitted by the real World preprocessor.

This does not synthesize assets or rewrite bytes. It adapts carefully selected
ARM assembler commentary and a redundant ARM-specific COMPOUND_STRING section
suffix to GNU x86 assembler syntax. No game data or GBA build is changed.
"""
import re

# Standalone @ comment (not an ARM instruction, symbol, or data literal).
STANDALONE_ARM_COMMENT = re.compile(r"(?P<indent>[ \t]*)@(?=[ \t]|$)(?P<tail>[^\r\n]*)$")
# At end of a data directive, only whitespace followed by an @ comment.
DIRECTIVE_ARM_COMMENT = re.compile(
    r"(?P<head>[ \t]*\.[A-Za-z][^\r\n]*?)[ \t]+@(?=[ \t]|$)(?P<tail>[^\r\n]*)$"
)
# Real World compound string generated assembly has an ARM-only section suffix.
# Preserve the mergeable section, including the stride and embedded byte data.
ARM_COMPOUND_SECTION = re.compile(
    r'(?P<section>[ \t]*\.section[ \t]+\.rodata\.compound_string\.[A-Za-z0-9_]+,'
    r'"aM",%progbits,[1-9][0-9]*)[ \t]+@,"a"$'
)


def normalize_host_assembly(source):
    """Return (normalized_source, line_count) with byte directives untouched."""
    lines = []
    changed = 0
    for line in source.splitlines(keepends=True):
        payload = line.rstrip("\r\n")
        eol = line[len(payload):]
        compound = ARM_COMPOUND_SECTION.fullmatch(payload)
        if compound:
            lines.append(compound.group("section") + eol)
            changed += 1
            continue
        standalone = STANDALONE_ARM_COMMENT.fullmatch(payload)
        if standalone:
            lines.append(standalone.group("indent") + "#" + standalone.group("tail") + eol)
            changed += 1
            continue
        match = DIRECTIVE_ARM_COMMENT.fullmatch(payload)
        if match:
            prefix = match.group("head")
            # Avoid a quoted @ in .ascii/.incbin (or an odd quote sequence).
            if prefix.count('"') % 2 == 0 and prefix.count("'") % 2 == 0:
                lines.append(prefix + " #" + match.group("tail") + eol)
                changed += 1
                continue
        lines.append(line)
    return "".join(lines), changed
