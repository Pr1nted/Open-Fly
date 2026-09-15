"""Strip a stylesheet down for itch.io's CSS box, without touching what it says.

    python3 tools/minify_css.py docs/itch/theme.css -o docs/itch/theme.min.css

docs/itch/theme.css is the source and stays fully commented: it is where the
selectors are explained, and itch's internal class names move, so the notes are
worth more than the bytes. This writes the paste-ready copy.

STRING AWARE, AND ONLY IN ONE PASS, WHICH IS THE PART THAT MATTERS. The theme
puts structural punctuation inside quoted content: the title bar is
"pr1nted@itch.io:~/open-fly$ ./open-fly --watch", and the ticker runs
"... LEAKY INTEGRATE-AND-FIRE, SHIU ET AL. 2024 ...". A tidy-up pass like

    re.sub(r" ?([{};,>]) ?", r"\\1", css)

cannot tell those commas from a selector's, so it rewrites the ticker to
"INTEGRATE-AND-FIRE,SHIU" -- the page still loads, the CSS is still valid, and
the text scrolling across the header is quietly not what was written. So the
spacing decisions happen in the walk below, where quoted runs are copied out
whole and never looked at again. Nothing rewrites the output afterwards.

Order is preserved, so the @import stays the first rule, which CSS requires.
"""
import argparse
import re

# Punctuation that never needs a space beside it in CSS.
STRUCT = "{};,>"


def minify(css):
    out = []
    i, n = 0, len(css)

    def significant_at(k):
        """The next character that is not whitespace or a comment, from k."""
        while k < n:
            if css.startswith("/*", k):
                end = css.find("*/", k + 2)
                k = n if end == -1 else end + 2
                continue
            if css[k].isspace():
                k += 1
                continue
            return css[k]
        return ""

    while i < n:
        # A comment goes, whatever is inside it.
        if css.startswith("/*", i):
            end = css.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue

        c = css[i]

        # A quoted string is copied out whole, escapes and all, and is never
        # touched again.
        if c in "\"'":
            quote, j = c, i + 1
            while j < n:
                if css[j] == "\\":
                    j += 2
                    continue
                if css[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(css[i:j])
            i = j
            continue

        # Whitespace survives only where removing it would join two tokens.
        if c.isspace():
            j = i
            while j < n and css[j].isspace():
                j += 1
            prev = out[-1] if out else ""
            nxt = significant_at(j)
            # Not after punctuation or an open bracket, not before punctuation
            # or a closing bracket. A space before "(" stays: "@media (" needs it.
            if (prev and prev not in STRUCT + ":(" and nxt and nxt not in STRUCT + ":)"):
                out.append(" ")
            i = j
            continue

        # Punctuation: drop any space that ended up in front of it.
        if c in STRUCT or c == ":":
            while out and out[-1] == " ":
                out.pop()
            out.append(c)
            i += 1
            continue

        out.append(c)
        i += 1

    return "".join(out).replace(";}", "}").strip() + "\n"


def check(source, small):
    """Refuse to ship a stylesheet that lost something. A truncated or mangled
    paste takes the whole theme down, not one rule, and the damage is invisible
    until someone reads the page."""
    problems = []
    if source.count("{") != small.count("{"):
        problems.append(f"rule count changed: {source.count('{')} -> {small.count('{')}")
    if small.count("{") != small.count("}"):
        problems.append("unbalanced braces")

    # Every quoted string in the source must appear, byte for byte, in the
    # output. This is the check that catches a tidy-up pass editing the ticker.
    src_strings = re.findall(r'"(?:[^"\\]|\\.)*"', strip_comments(source))
    for s in src_strings:
        if s not in small:
            problems.append(f"string altered or lost: {s[:60]}")

    if not small.lstrip().startswith("@import"):
        problems.append("@import is no longer first")
    return problems


def strip_comments(css):
    out, i, n = [], 0, len(css)
    while i < n:
        if css.startswith("/*", i):
            end = css.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if css[i] in "\"'":
            quote, j = css[i], i + 1
            while j < n:
                if css[j] == "\\":
                    j += 2
                    continue
                if css[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(css[i:j])
            i = j
            continue
        out.append(css[i])
        i += 1
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    css = open(args.source, encoding="utf-8").read()
    small = minify(css)

    problems = check(css, small)
    if problems:
        for p in problems:
            print(f"  {p}")
        raise SystemExit("minify: refusing to write")

    open(args.out, "w", encoding="utf-8").write(small)
    print(f"{args.source}: {len(css):,} bytes -> {args.out}: {len(small):,} "
          f"({100 * len(small) / len(css):.0f}%), {small.count('{')} rules")


if __name__ == "__main__":
    main()
