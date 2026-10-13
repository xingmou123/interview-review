"""Offline regression tests: no network, real CLI, learner IDs or private links."""
import copy
import html
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import review_gate as gate


def xml(value):
    return '<p><span text-color="purple">' + html.escape(value) + '</span></p>'


def plan(value='建议：收到 ACK 后再检查执行批次，确认目标是否进入控制环'):
    return {'document': 'TestDocument', 'revision': 4, 'operations': [
        {'command': 'block_replace', 'block_id': 'advice', 'expected_text': '建议：', 'content': xml(value)}]}


def reviewed(p):
    return {'plan_sha256': gate.digest(p), 'reviewer': 'offline-test-fixture',
            'checks': {k: True for k in gate.CHECKS}, 'findings': []}


class FakeLark:
    def __init__(self):
        self.root = ET.fromstring('<root><h1 id="heading">项目问题</h1><h2 id="question">Q1</h2>'
                                 '<p id="answer">回答：这里不是实测数据</p>'
                                 '<p id="advice">建议：</p><p id="user">建议：没问题</p>'
                                 '<figure id="audio"><source token="kept"/></figure></root>')
        self.revision, self.writes, self.fetches = 4, 0, 0
        self.before_second_read = None
        self.after_write = None
        self.warning = False
        self.colors = ('purple', gate.COLOR)

    def fetch(self, document):
        self.fetches += 1
        if self.fetches == 2 and self.before_second_read:
            self.before_second_read(self)
        return {'ok': True, 'data': {'document': {
            'revision_id': self.revision, 'content': ''.join(ET.tostring(n, encoding='unicode') for n in self.root)}}}

    def update(self, document, revision, op):
        assert self.revision == revision
        self.writes += 1
        old = next(n for n in self.root if n.get('id') == op['block_id'])
        index = list(self.root).index(old)
        if op['command'] == 'block_replace':
            self.root.remove(old)
        else:
            index += 1
        for j, n in enumerate(gate.fragment(op['content'], *self.colors)):
            n.set('id', f'new{self.writes}p{j}')
            for s in n.iter('span'):
                s.set('text-color', self.colors[1])
            self.root.insert(index + j, n)
        self.revision += 1
        if self.after_write:
            self.after_write(self)
        return {'ok': True, 'data': {'result': 'success', 'warnings': ['partial formatting'] if self.warning else []}}


class ProseTests(unittest.TestCase):
    def test_new_prose_rejects_double_quotes_but_keeps_code_syntax(self):
        for value in ('他说“可以启动”', '他说"可以启动"', '他说＂可以启动＂'):
            with self.subTest(value=value):
                result = gate.check(plan(value))
                self.assertFalse(result['passed'])
                self.assertEqual(result['findings'][0]['rule'], 'double_quote')
        p = plan()
        p['operations'][0]['content'] = '<p><span text-color="purple">判断条件见 <code>state == "ready"</code>，随后发送指令</span></p>'
        self.assertTrue(gate.check(p)['passed'])

    def test_rejected_historical_failures_and_paraphrases(self):
        bad = [
            '这里的 41% 是设计预算，70% 是压力测试条件，不是已经测出的现场成绩',
            '这里不是实测数据，不能当成项目成绩',
            '这些数字只能用于理解，不要说成自己测过',
            '以上是按项目结构补的调试示范，数字用于解释时间关系',
            '这个例子讲的是越界机制，不是断言原项目用了这个间距',
            '没有给出具体回归次数，不需要为了显得完整编一个次数',
            '这只是示例数字，不是这次项目的实绩',
            '不能把这组数字写成自己做过的结果',
            '没有原始日志，所以只能说设计目标',
            '请学员自己核对配置和实测数据后再回答',
            '这里不\u200b是 实 测 数 据',
            '这是 AI 生成的参考答案',
            '这个数值来自课堂推演，面试时请把它与亲身项目经验分开',
            '先把配置查清楚，再组织答案',
        ]
        for value in bad:
            with self.subTest(value=value):
                self.assertFalse(gate.check(plan(value))['passed'])

    def test_keep_technical_distinctions_and_useful_answers(self):
        good = [
            '正常总线预算约 41%，压力测试提高到 70%，观察命令排队和执行时间',
            '81 ms 对应撤去主动出力；机械停稳还受惯量和腱绳储能影响',
            'CAN 硬件 ACK 不代表控制器已经执行命令',
            '例如，收到批次 125，而执行批次仍为 124，说明目标尚未生效',
            '实测电流噪声增大时，对齐 PWM 与 ADC 采样时刻检查开关干扰',
            '没有收到心跳不能证明电机已经停止，应该检查 PWM 和轴反馈',
            '不要在中断里获取互斥锁，使用 FromISR 通知处理任务',
            '建议：没问题',
            '假设每半区128点，采样12.8kHz，处理任务有10ms窗口',
            '先确认输入车速与查表索引，再检查边界处理',
            '这些数据只用于计算平均电流，过流保护仍然使用逐点采样值',
            '这些数据不代表过流故障，需要结合阈值和持续时间判断',
        ]
        for value in good:
            with self.subTest(value=value):
                self.assertTrue(gate.check(plan(value))['passed'])

    def test_rich_text_cannot_split_a_disclaimer(self):
        p = plan()
        p['operations'][0]['content'] = '<p><span text-color="purple">不是</span><b><span text-color="purple">实测数据</span></b></p>'
        self.assertFalse(gate.check(p)['passed'])

    def test_empty_answers_opaque_resources_and_hidden_text_rejected(self):
        for content in ['', '<p/>', xml('建议：'), '<img src="token"/>', '<p title="不是实测数据">说明</p>',
                        '<p><span text-color="purple">有效答案</span>黑色漏检文字</p>',
                        '<!DOCTYPE p [<!ENTITY x "x">]><p>&x;</p>']:
            with self.subTest(content=content):
                p = plan()
                p['operations'][0]['content'] = content
                with self.assertRaises(gate.GateError): gate.check(p)


class PublishTests(unittest.TestCase):
    def run_publish(self, p=None, r=None, fake=None):
        p = p or plan()
        fake = fake or FakeLark()
        with tempfile.TemporaryDirectory() as tmp:
            return gate.publish(p, reviewed(p) if r is None else r, fake, Path(tmp) / 'audit')

    def test_reject_before_cli_even_if_semantic_form_claims_pass(self):
        fake = FakeLark()
        p = plan('这里不是实测数据')
        with self.assertRaises(gate.GateError): self.run_publish(p, reviewed(p), fake)
        self.assertEqual((fake.fetches, fake.writes), (0, 0))

    def test_user_selected_color_is_checked_and_published(self):
        p = plan()
        p['review_style'] = {'color': 'blue', 'readback_color': 'rgb(36,91,219)', 'basis': '离线夹具：用户要求蓝色，源样式提供 RGB'}
        p['operations'][0]['content'] = p['operations'][0]['content'].replace('purple', 'blue')
        fake = FakeLark()
        fake.colors = ('blue', 'rgb(36,91,219)')
        self.assertTrue(gate.check(p)['passed'])
        self.assertEqual(self.run_publish(p, fake=fake)['published'], 1)
        p['review_style']['basis'] = ''
        with self.assertRaises(gate.GateError): gate.check(p)

    def test_missing_semantic_review_rejects_without_cli(self):
        fake = FakeLark()
        with self.assertRaises(gate.GateError): self.run_publish(r={}, fake=fake)
        self.assertEqual((fake.fetches, fake.writes), (0, 0))

    def test_changed_draft_invalidates_review(self):
        p = plan()
        r = reviewed(p)
        p['operations'][0]['content'] = xml('另一个技术答案')
        fake = FakeLark()
        with self.assertRaises(gate.GateError): self.run_publish(p, r, fake)
        self.assertEqual(fake.writes, 0)

    def test_fail_or_unresolved_review_rejects(self):
        p = plan()
        for key in gate.CHECKS:
            r = reviewed(p)
            r['checks'][key] = False
            with self.subTest(key=key), self.assertRaises(gate.GateError): self.run_publish(p, r)
        r = reviewed(p)
        r['findings'] = ['答案删空']
        with self.assertRaises(gate.GateError): self.run_publish(p, r)

    def test_remote_revision_and_original_text_must_match(self):
        for change in ('revision', 'text'):
            fake = FakeLark()
            if change == 'revision': fake.revision += 1
            else: next(n for n in fake.root if n.get('id') == 'advice').text = '建议：用户的新修改'
            with self.subTest(change=change), self.assertRaises(gate.GateError): self.run_publish(fake=fake)
            self.assertEqual(fake.writes, 0)

    def test_preserve_original_answers_even_when_they_contain_flagged_words(self):
        fake = FakeLark()
        next(n for n in fake.root if n.get('id') == 'answer').text = '回答：这里不是实测数据，他说“看中断”'
        r = self.run_publish(fake=fake)
        self.assertEqual(r['published'], 1)
        self.assertEqual(next(n for n in fake.root if n.get('id') == 'answer').text, '回答：这里不是实测数据，他说“看中断”')
        self.assertEqual(next(n for n in fake.root if n.get('id') == 'user').text, '建议：没问题')
        self.assertIsNotNone(next(n for n in fake.root if n.get('id') == 'audio').find('source'))

    def test_original_question_answer_cannot_be_replaced(self):
        p = plan()
        p['operations'][0].update(block_id='answer', expected_text='回答：这里不是实测数据')
        fake = FakeLark()
        with self.assertRaises(gate.GateError): self.run_publish(p, fake=fake)
        self.assertEqual(fake.writes, 0)

    def test_insert_multiple_paragraphs_preserves_anchor_and_order(self):
        p = plan()
        p['operations'][0].update(command='block_insert_after', block_id='answer', expected_text='回答：这里不是实测数据', content=xml('建议：检查执行批次') + xml('记录目标从接收到执行的时间'))
        fake = FakeLark()
        self.run_publish(p, fake=fake)
        values = [gate.text(n) for n in fake.root]
        self.assertEqual(values[2:6], ['回答：这里不是实测数据', '建议：检查执行批次', '记录目标从接收到执行的时间', '建议：'])

    def test_concurrent_edit_before_write_stops(self):
        fake = FakeLark()
        fake.before_second_read = lambda f: setattr(f, 'revision', f.revision + 1)
        with self.assertRaises(gate.GateError): self.run_publish(fake=fake)
        self.assertEqual(fake.writes, 0)

    def test_remote_warning_stops_without_retry(self):
        fake = FakeLark()
        fake.warning = True
        with self.assertRaises(gate.GateError): self.run_publish(fake=fake)
        self.assertEqual(fake.writes, 1)
        self.assertEqual(fake.fetches, 3)

    def test_readback_wrong_text_color_or_original_change_is_detected(self):
        for fault in ('text', 'color', 'uncolored_tail', 'original'):
            fake = FakeLark()
            def corrupt(f):
                if fault == 'text': next(n for n in f.root if n.get('id') == 'new1p0').find('span').text = '错误正文'
                elif fault == 'color': next(n for n in f.root if n.get('id') == 'new1p0').find('span').set('text-color', 'red')
                elif fault == 'uncolored_tail':
                    s = next(n for n in f.root if n.get('id') == 'new1p0').find('span')
                    s.tail = s.text[-4:]
                    s.text = s.text[:-4]
                else: next(n for n in f.root if n.get('id') == 'user').text = '被覆盖'
            fake.after_write = corrupt
            with self.subTest(fault=fault), self.assertRaises(gate.GateError): self.run_publish(fake=fake)
            self.assertEqual(fake.writes, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
