"""Check learner prose and publish reviewed paragraph patches. Python stdlib only."""
import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

CHECKS = ('no_author_meta', 'answers_useful', 'technical_meaning_preserved', 'user_edits_preserved')
COLOR = 'rgb(100,37,208)'
RULES = {
    'historical_disclaimer': r'(?:不是|并非|不代表|不等于|不能当成|不能作为|不应当作|不属于)[^。！？\n]{0,45}(?:实测(?:数据|结果|结论|成绩)|已经测出|现场成绩|个人经历|项目实绩|真实经历|项目成绩)',
    'example_disclaimer': r'(?:只是|仅是|仅供|只供)[^。！？\n]{0,20}(?:示例|举例|示范|教学)|(?:示例|示范|假设)[^。！？\n]{0,30}(?:不是|不能|不要)[^。！？\n]{0,30}(?:经历|实绩|实测|做过|测过)',
    'numbers_disclaimer': r'(?:数字|数据|例子)[^。！？\n]{0,25}(?:用于理解|用于解释|不是断言)|(?:不要|不能|不可|切勿|别|不应)[^。！？\n]{0,20}(?:当成|说成|写成)[^。！？\n]{0,20}(?:自己|本人|项目|实际|已经)[^。！？\n]{0,15}(?:测过|做过|发生|成绩|实测|经历)',
    'experience_separation': r'(?:面试|回答)[^。！？\n]{0,25}(?:与|和)[^。！？\n]{0,12}(?:亲身|实际|真实|个人)[^。！？\n]{0,8}(?:经验|经历)[^。！？\n]{0,8}(?:分开|区分)',
    'fabrication_lecture': r'(?:不要|不能|不应|不需要|不可|别|切勿)[^。！？\n]{0,25}(?:编造|编一个|编个|另造)[^。！？\n]{0,20}(?:数据|数字|次数|经历|故事|结果)?',
    'evidence_lecture': r'(?:没有|缺少|缺乏|未提供)[^。！？\n]{0,20}(?:证据|记录|日志|实测)[^。！？\n]{0,35}(?:只能说|只能写|不能说|不能写|不要说)',
    'deferred_answer': r'(?:你|学员|自行|自己)[^。！？\n]{0,12}(?:核对|确认|补充)[^。！？\n]{0,20}(?:配置|实测|数据|证据)[^。！？\n]{0,12}(?:再回答|再说|再填)|(?:配置|数据|实测)[^。！？\n]{0,8}(?:查清楚|核对清楚)[^。！？\n]{0,8}(?:再组织答案|再回答)',
    'production_meta': r'AI\s*生成|内部底稿|制作过程|教师备注|不是另做一个市场薪资判断|以上是按项目结构补的调试示范|讲已实现部分时要',
}


class GateError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(plan):
    raw = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def text(node):
    return ''.join(node.itertext())


def text_without_code(node):
    """Collect visible prose while keeping inline code syntax out of prose checks."""
    parts = []

    def walk(current):
        if current.tag != 'code' and current.text:
            parts.append(current.text)
        for child in current:
            if child.tag != 'code':
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(node)
    return ''.join(parts)


def review_colors(plan):
    style = plan.get('review_style')
    if style is None:
        return 'purple', COLOR
    if not isinstance(style, dict) or not isinstance(style.get('basis'), str) or not style['basis'].strip():
        raise GateError('Color override needs the user instruction or existing style source')
    name, rgb = style.get('color'), style.get('readback_color')
    if name not in ('red', 'orange', 'yellow', 'green', 'blue', 'purple', 'gray'):
        raise GateError('Unsupported review color')
    if not isinstance(rgb, str) or not re.fullmatch(r'rgb\(\d{1,3},\d{1,3},\d{1,3}\)', rgb) or any(int(v) > 255 for v in re.findall(r'\d+', rgb)):
        raise GateError('Provide the exact RGB value observed in the existing document style')
    return name, rgb


def all_text_colored(node, colors, inherited=False):
    color = node.get('text-color')
    colored = color in colors if color is not None else inherited
    if node.text and node.text.strip() and not colored:
        return False
    for child in node:
        if not all_text_colored(child, colors, colored):
            return False
        if child.tail and child.tail.strip() and not colored:
            return False
    return True


def normalize(value):
    value = unicodedata.normalize('NFKC', value)
    return ''.join(c for c in value if not c.isspace() and unicodedata.category(c) != 'Cf')


def prose_findings(paragraphs):
    found = []
    for index, paragraph in enumerate(paragraphs):
        s = normalize(paragraph)
        for rule, pattern in RULES.items():
            if re.search(pattern, s, re.I):
                found.append({'paragraph': index + 1, 'rule': rule, 'text': paragraph})
    return found


def fragment(content, color='purple', readback_color=COLOR):
    if not isinstance(content, str) or len(content) > 200000 or re.search(r'<!|<\?', content):
        raise GateError('Invalid or oversized XML fragment')
    try:
        root = ET.fromstring('<root>' + content + '</root>')
    except ET.ParseError as e:
        raise GateError('Invalid XML: ' + str(e)) from e
    if root.text and root.text.strip():
        raise GateError('Text must be inside paragraphs')
    allowed = {'p': set(), 'span': {'text-color'}, 'b': set(), 'em': set(), 'u': set(), 'code': set(), 'br': set(), 'a': {'href'}}

    def walk(n, inherited=False):
        if n.tag not in allowed or set(n.attrib) - allowed[n.tag]:
            raise GateError('Only visible paragraph text and simple inline formatting are supported')
        colored = inherited
        if 'text-color' in n.attrib:
            if n.get('text-color') not in (color, readback_color):
                raise GateError('New review text must match the selected review color')
            colored = True
        if n.text and n.text.strip() and not colored:
            raise GateError('Uncolored review text')
        for c in n:
            if c.tag == 'p':
                raise GateError('Nested paragraphs are unsupported')
            walk(c, colored)
            if c.tail and c.tail.strip() and not colored:
                raise GateError('Uncolored review text')
    children = list(root)
    if not children:
        raise GateError('Empty replacement is not a content fix')
    for n in children:
        if n.tag != 'p' or not normalize(text(n)) or (n.tail and n.tail.strip()):
            raise GateError('Each added block must be a nonempty paragraph')
        if normalize(text(n)) == '建议:':
            raise GateError('New empty advice is not a completed answer; leave user-cleared blocks untouched')
        walk(n)
    return children


def check(plan):
    if not isinstance(plan, dict) or not re.fullmatch(r'[A-Za-z0-9]+', str(plan.get('document', ''))):
        raise GateError('Use the document token, not a URL')
    if type(plan.get('revision')) is not int or plan['revision'] < 0:
        raise GateError('An explicit current revision is required')
    ops = plan.get('operations')
    if not isinstance(ops, list) or not ops:
        raise GateError('No operations to review')
    ids, findings = set(), []
    colors = review_colors(plan)
    for index, op in enumerate(ops):
        if not isinstance(op, dict) or op.get('command') not in ('block_replace', 'block_insert_after'):
            raise GateError('Only single-block replace and insert-after are supported')
        bid = op.get('block_id')
        if not isinstance(bid, str) or not re.fullmatch(r'[A-Za-z0-9]+', bid) or bid in ids:
            raise GateError('Each source block must appear once')
        ids.add(bid)
        if not isinstance(op.get('expected_text'), str):
            raise GateError('Expected original text is required')
        nodes = fragment(op.get('content'), *colors)
        for issue in prose_findings([text(n) for n in nodes]):
            findings.append({'operation': index + 1, **issue})
        for paragraph, node in enumerate(nodes, 1):
            if re.search(r'["“”＂]', text_without_code(node)):
                findings.append({'operation': index + 1, 'paragraph': paragraph,
                                 'rule': 'double_quote', 'text': text(node)})
    return {'passed': not findings, 'plan_sha256': digest(plan), 'operations': len(ops), 'findings': findings,
            'scope': 'format and known prose patterns; semantic review still required'}


def validate_review(plan, review):
    if not isinstance(review, dict) or review.get('plan_sha256') != digest(plan):
        raise GateError('Semantic review is missing or belongs to a different draft')
    if not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip():
        raise GateError('Identify who actually reviewed the draft')
    if review.get('findings') != [] or not isinstance(review.get('checks'), dict):
        raise GateError('Unresolved semantic findings')
    if any(review['checks'].get(k) is not True for k in CHECKS):
        raise GateError('Every semantic criterion must pass after actual review')


def doc_nodes(obj):
    return list(ET.fromstring('<root>' + obj['data']['document']['content'] + '</root>'))


def canon(n):
    n = copy.deepcopy(n)
    for e in n.iter():
        e.attrib.pop('id', None)
    return ET.tostring(n, encoding='unicode')


class Lark:
    def __init__(self, executable=None):
        self.executable = executable or shutil.which('lark-cli')
        if not self.executable:
            raise GateError('lark-cli not found')

    def call(self, args):
        p = subprocess.run([self.executable] + args + ['--as', 'user'], capture_output=True, encoding='utf-8', timeout=120)
        if p.returncode:
            raise GateError(p.stderr or p.stdout)
        try:
            obj = json.loads(p.stdout)
        except ValueError as e:
            raise GateError('Ambiguous CLI result; read remote state before retry') from e
        if not obj.get('ok'):
            raise GateError(str(obj))
        return obj

    def fetch(self, document):
        return self.call(['docs', '+fetch', '--doc', document, '--detail', 'full'])

    def update(self, document, revision, operation):
        # Freeze checked content in a private temporary file; never re-read a mutable source file
        with tempfile.TemporaryDirectory(prefix='interview-review-') as tmp:
            path = Path(tmp) / 'patch.xml'
            path.write_text(operation['content'], encoding='utf-8')
            return self.call(['docs', '+update', '--doc', document, '--command', operation['command'],
                             '--block-id', operation['block_id'], '--revision-id', str(revision), '--content', '@' + str(path)])


def save_audit(folder, name, obj):
    (folder / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def publish(plan, review, transport, audit_dir):
    plan, review = copy.deepcopy(plan), copy.deepcopy(review)
    result = check(plan)
    if not result['passed']:
        raise GateError(json.dumps(result, ensure_ascii=False))
    validate_review(plan, review)
    colors = review_colors(plan)
    audit = Path(audit_dir)
    audit.mkdir(parents=True, exist_ok=True)
    if any(audit.iterdir()):
        raise GateError('Use an empty audit directory; inspect prior results before resuming')
    save_audit(audit, 'plan.json', plan)
    save_audit(audit, 'semantic-review.json', review)
    before = transport.fetch(plan['document'])
    save_audit(audit, 'before.json', before)
    revision = before['data']['document']['revision_id']
    if revision != plan['revision']:
        raise GateError('Remote revision changed; re-read user edits and rebuild the plan')
    lookup = {n.get('id'): n for n in doc_nodes(before)}
    for op in plan['operations']:
        if op['block_id'] not in lookup or text(lookup[op['block_id']]) != op['expected_text']:
            raise GateError('Original target text changed')
        if op['command'] == 'block_replace':
            target = lookup[op['block_id']]
            is_advice = text(target).strip().startswith('建议') or any(s.get('text-color') in ('purple', COLOR, *colors) for s in target.iter('span'))
            if target.tag != 'p' or not is_advice:
                raise GateError('Replace only existing advice paragraphs; preserve original questions and answers')
    completed = 0
    for index, op in enumerate(plan['operations'], 1):
        fresh = transport.fetch(plan['document'])
        if fresh['data']['document']['revision_id'] != revision:
            raise GateError('Concurrent edit detected before write; no automatic retry')
        old_nodes = doc_nodes(fresh)
        target_index = next(i for i, n in enumerate(old_nodes) if n.get('id') == op['block_id'])
        if text(old_nodes[target_index]) != op['expected_text']:
            raise GateError('Target changed before write')
        replacement = fragment(op['content'], *colors)
        replaced = op['command'] == 'block_replace'
        insert_index = target_index if replaced else target_index + 1
        protected = [n for i, n in enumerate(old_nodes) if not (replaced and i == target_index)]
        save_audit(audit, f'before-{index:03}.json', fresh)
        response = transport.update(plan['document'], revision, op)
        save_audit(audit, f'write-{index:03}.json', response)
        after = transport.fetch(plan['document'])
        save_audit(audit, f'after-{index:03}.json', after)
        if response.get('data', {}).get('result') != 'success' or response['data'].get('warnings'):
            raise GateError('Write warning or partial result; inspect readback before retry')
        actual = doc_nodes(after)
        if len(actual) != len(protected) + len(replacement):
            raise GateError('Unexpected block count after write')
        added = actual[insert_index:insert_index + len(replacement)]
        for expected, got in zip(replacement, added):
            if got.tag != 'p' or text(expected) != text(got):
                raise GateError('Published text or position differs from reviewed draft')
            spans = list(got.iter('span'))
            if not spans or not all_text_colored(got, colors):
                raise GateError('Published color differs from the selected review color')
        remainder = actual[:insert_index] + actual[insert_index + len(replacement):]
        if [(n.get('id'), canon(n)) for n in remainder] != [(n.get('id'), canon(n)) for n in protected]:
            raise GateError('Original content, style or order changed; inspect concurrent edits')
        revision = after['data']['document']['revision_id']
        completed += 1
        save_audit(audit, 'progress.json', {'completed': completed, 'revision': revision})
    summary = {'passed': True, 'published': completed, 'revision': revision, 'plan_sha256': digest(plan)}
    save_audit(audit, 'verification.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('check', 'publish'):
        p = sub.add_parser(command)
        p.add_argument('--plan', required=True)
        if command == 'publish':
            p.add_argument('--review', required=True)
            p.add_argument('--audit-dir', required=True)
            p.add_argument('--lark-cli')
    args = parser.parse_args()
    try:
        plan = read_json(args.plan)
        if args.command == 'check':
            result = check(plan)
        else:
            # Validate before even constructing the CLI transport
            report = check(plan)
            if not report['passed']:
                raise GateError(json.dumps(report, ensure_ascii=False))
            review = read_json(args.review)
            validate_review(plan, review)
            result = publish(plan, review, Lark(args.lark_cli), args.audit_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['passed'] else 2
    except (GateError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as e:
        print(json.dumps({'passed': False, 'error': str(e)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == '__main__':
    sys.exit(main())
