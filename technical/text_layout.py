"""Rebalance diary lines to even pixel widths; line count and blank lines stay fixed."""


def balance(words, count, measure, space):
    """Split words into exactly count lines, narrowest widest line first."""
    widths = [measure(word) for word in words]
    prefix = [0]
    for width in widths:
        prefix.append(prefix[-1]+width)
    span = lambda i, j: prefix[j]-prefix[i]+space*(j-i-1)
    best = {(1, j): ((span(0, j), span(0, j)**2), 0) for j in range(1, len(words)+1)}
    for line in range(2, count+1):
        for j in range(line, len(words)+1):
            options = []
            for i in range(line-1, j):
                (widest, squares), _ = best[line-1, i]
                width = span(i, j)
                options.append(((max(widest, width), squares+width**2), i))
            best[line, j] = min(options, key=lambda option: option[0])
    cuts, j = [], len(words)
    for line in range(count, 0, -1):
        i = best[line, j][1]
        cuts.append((i, j))
        j = i
    return [' '.join(words[i:j]) for i, j in reversed(cuts)]


def reflow(text, measure, space):
    """Rebalance each run of non-blank lines; a run with too few words is kept."""
    lines = text.split('\n')
    out, start = [], 0
    while start < len(lines):
        if not lines[start].strip():
            out.append(lines[start])
            start += 1
            continue
        end = start
        while end < len(lines) and lines[end].strip():
            end += 1
        block = lines[start:end]
        words = ' '.join(block).split()
        out.extend(balance(words, len(block), measure, space) if 1 < len(block) <= len(words) else block)
        start = end
    return '\n'.join(out)
