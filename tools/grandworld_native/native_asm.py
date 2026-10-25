"""Translate ARM-style end-of-line assembly COMMENTS from the World preprocessor.

The real World's text/graphics preprocessor can emit data directives with
' @ comment', accepted by GNU ARM assembler but not x86 GNU assembler.
Only full-line assembler DIRECTIVES with a whitespace-delimited @ comment
are changed; bytes, incbin paths, quoted strings and actual instructions
must remain untouched. This is a host assembler syntax adapter, NOT an
asset placeholder or a content converter.
"""
import re

COMMENT = re.compile(r"(?P<head>\s*\.[A-Za-z][^\n]*?)\s+@(?=\s|$)(?P<tail>[^\n]*)$")
STANDALONE_ARM_COMMENT = re.compile(r"(?P<indent>\s*)@(?=\s|$)(?P<tail>[^\n]*)$")
# The World charmap COMPOUND_STRING resource macro emits an ARM-only suffix.
# Keep the original mergeable section and byte stride untouched.
ARM_COMPOUND_SECTION = re.compile(
    r'(?P<section>\s*\.section\s+\.rodata\.compound_string\.[A-Za-z0-9_]+,"aM",%progbits,[1-9][0-9]*)\s+@,"a"

def normalize_host_assembly(source):
    lines = []
    adapted = 0
    for line in source.splitlines(keepends=True):
        payload = line.rstrip("\r\n")
        eol = line[len(payload):]
        compound = ARM_COMPOUND_SECTION.fullmatch(payload)
        if compound:
            lines.append(compound.group("section") + eol)
            adapted += 1
            continue
        standalone = STANDALONE_ARM_COMMENT.fullmatch(payload)
        if standalone:
            line = standalone.group("indent") + "#" + standalone.group("tail") + eol
            adapted += 1
            lines.append(line)
            continue
        match = COMMENT.fullmatch(payload)
        if match:
            # Never risk altering an @ inside a string literal, .incbin path
            # or symbol name. Only directives and comments may be adapted.
            prefix = match.group("head")
            if prefix.count('"') % 2 == 0 and prefix.count("'") % 2 == 0:
                line = prefix + " #" + match.group("tail") + eol
                adapted += 1
        lines.append(line)
    return "".join(lines), adapted

)

def normalize_host_assembly(source):
    lines = []
    adapted = 0
    for line in source.splitlines(keepends=True):
        payload = line.rstrip("\r\n")
        eol = line[len(payload):]
        standalone = STANDALONE_ARM_COMMENT.fullmatch(payload)
        if standalone:
            line = standalone.group("indent") + "#" + standalone.group("tail") + eol
            adapted += 1
            lines.append(line)
            continue
        match = COMMENT.fullmatch(payload)
        if match:
            # Never risk altering an @ inside a string literal, .incbin path
            # or symbol name. Only directives and comments may be adapted.
            prefix = match.group("head")
            if prefix.count('"') % 2 == 0 and prefix.count("'") % 2 == 0:
                line = prefix + " #" + match.group("tail") + eol
                adapted += 1
        lines.append(line)
    return "".join(lines), adapted
