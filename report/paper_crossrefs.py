"""Link explicit numbered references without changing manuscript wording."""
import re


def inline_text(nodes):
    parts = []
    for node in nodes:
        kind = node.get('t')
        if kind == 'Str':
            parts.append(node['c'])
        elif kind in {'Space', 'SoftBreak', 'LineBreak'}:
            parts.append(' ')
        elif kind in {'Strong', 'Emph', 'SmallCaps'}:
            parts.append(inline_text(node['c']))
    return ''.join(parts)


def text_nodes(text):
    return [{'t': 'Space'} if bit == ' ' else {'t': 'Str', 'c': bit}
            for bit in re.split('( )', text) if bit]


def link_references(ast):
    targets, links = {}, []
    section = re.compile(r'^(\d+(?:\.\d+)*)(?:\. | )')
    appendix = re.compile(r'^([A-Z](?:\.\d+)*)(?:\. | )')
    caption = re.compile(r'^(Figure|Table) ([A-Z]\.\d+|\d+)\.')

    def collect(blocks):
        for block in blocks:
            kind = block.get('t')
            if kind == 'Header':
                text = inline_text(block['c'][2])
                match = section.match(text) or appendix.match(text)
                if match:
                    number = match[1]
                    prefix = 'app' if number[0].isalpha() else 'sec'
                    anchor = block['c'][1][0] or f'{prefix}-{number.replace(".", "-")}'
                    block['c'][1][0] = anchor
                    targets[('section', number)] = anchor
            elif kind in {'Para', 'Plain'}:
                match = caption.match(inline_text(block['c']))
                if match:
                    key = (match[1].lower(), match[2])
                    anchor = f'{key[0]}-{key[1].replace(".", "-")}'
                    if key in targets:
                        raise ValueError(f'Duplicate caption: {key}')
                    targets[key] = anchor
                    block['c'] = [{'t':'Span', 'c':[[anchor, [], []], block['c']]}]
            elif kind == 'Div':
                if 'prompt' not in block['c'][0][1]:
                    collect(block['c'][1])
            elif kind in {'BulletList', 'OrderedList'}:
                for item in (block['c'] if kind == 'BulletList' else block['c'][1]):
                    collect(item)
            elif kind == 'BlockQuote':
                collect(block['c'])
    collect(ast['blocks'])
    pattern = re.compile(r'(?<!\w)(Appendix|Section|§|Figure|Table)\s*([A-Z](?:\.\d+)*|\d+(?:\.\d+)*)(?![\w.]\w)')

    def convert(inlines):
        result, pending = [], []
        def flush():
            text = inline_text(pending)
            cursor = 0
            for match in pattern.finditer(text):
                label, number = match.groups()
                kind = label.lower() if label in {'Figure', 'Table'} else 'section'
                target = targets.get((kind, number))
                if not target:
                    continue
                result.extend(text_nodes(text[cursor:match.start()]))
                result.append({'t':'Link', 'c':[['', [], []], text_nodes(match[0]), ['#'+target, '']]})
                links.append({'text': match[0], 'target': target})
                cursor = match.end()
            result.extend(text_nodes(text[cursor:]))
            pending.clear()
        for node in inlines:
            if node.get('t') in {'Str', 'Space', 'SoftBreak'}:
                pending.append(node)
            else:
                flush()
                if node.get('t') in {'Strong', 'Emph', 'SmallCaps'}:
                    node['c'] = convert(node['c'])
                result.append(node)
        flush()
        return result

    def visit(node):
        if isinstance(node, dict):
            kind = node.get('t')
            if kind in {'Header', 'CodeBlock', 'Code', 'Link', 'Cite'}:
                return
            if kind == 'Div' and 'prompt' in node['c'][0][1]:
                return
            if kind in {'Para', 'Plain'}:
                # Caption spans are destinations, not references to themselves.
                if not (node['c'] and node['c'][0].get('t') == 'Span' and
                        node['c'][0]['c'][0][0].startswith(('figure-', 'table-'))):
                    node['c'] = convert(node['c'])
                return
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(ast['blocks'])
    return {'targets': {f'{k[0]} {k[1]}': v for k, v in targets.items()}, 'links': links}
