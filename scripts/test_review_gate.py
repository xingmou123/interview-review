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
        children = list(self.root)
        if 'start_block_id' in op:
            s_idx = next(i for i, n in enumerate(children) if n.get('id') == op['start_block_id'])
            e_idx = next(i for i, n in enumerate(children) if n.get('id') == op['end_block_id'])
            for old in children[s_idx:e_idx + 1]:
                self.root.remove(old)
            index = s_idx
        else:
            old = next(n for n in children if n.get('id') == op['block_id'])
            index = children.index(old)
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
            '原答只讲了一半，这里漏了偏置原理',
            '3 分钟本场诊断卡：先看这三点',
            '考前 5 分钟速查卡：记住这几个公式',
            '这题暴露出三处关键技术硬伤',
            '这里满量程放太大了——平时电流很小',
            '另外核对 20 分钟完整录音，发现这里卡住了',
            '对照完整录音，这里没回答上追问',
            '今晚先把这几题吃透，把公式亲手推一遍',
            '同时立刻统一简历和口述口径，把架构收口，调低简历表述，绝不再出现否认的情况',
            '这里要把协作边界补透，真正落地过才敢写',
            '问题排查要形成闭环，做好闭环管理',
            '第一点看中断优先级；第二点看 DMA 通道；第三点看缓冲长度',
            '这里把整个串口接收状态机从空闲中断触发到环形缓冲写指针回绕再到主循环解析校验包头包尾以及异常超时复位全都揉在了一句超过九十五个字的超长说明里，不仅没有分句还没有换行，让学员读到一半根本喘不过气来彻底看晕过去',
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
            '听了一下录音，08:22 这里讲完空闲中断就停住了',
            '电机控制采用电流闭环和速度闭环串级结构，位置闭环在外层',
        ]
        for value in good:
            with self.subTest(value=value):
                self.assertTrue(gate.check(plan(value))['passed'])

    def test_bold_mentor_prefixes_and_natural_intro_pass(self):
        p = plan()
        p['operations'][0]['content'] = (
            '<p><b><span text-color="purple">建议：</span></b>'
            '<span text-color="purple">这里把分辨率和真实精度混在一起了</span></p>'
            '<p><b><span text-color="purple">参考回答：</span></b>'
            '<span text-color="purple">12 位 ADC 理论分辨率是 3.3 V ÷ 4096 ≈ 0.806 mV/LSB</span></p>'
            '<p><b><span text-color="purple">如果接着追问：</span></b>'
            '<span text-color="purple">电角度零位偏了 30° 会漏出一半转矩</span></p>'
        )
        self.assertTrue(gate.check(p)['passed'])
        fake = FakeLark()
        with tempfile.TemporaryDirectory() as tmp:
            summary = gate.publish(p, reviewed(p), fake, Path(tmp) / 'audit')
            self.assertTrue(summary['passed'])

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

    def test_paragraph_too_dense_rejected(self):
        dense = '这是一句很短的话。' * 34
        res = gate.check(plan(dense))
        self.assertFalse(res['passed'])
        self.assertEqual(res['findings'][0]['rule'], 'paragraph_too_dense')

    def test_range_replace_purple_advice_and_reject_original_in_range(self):
        fake = FakeLark()
        fake.root = ET.fromstring(
            '<root><h2 id="q1">Q1</h2><p id="a1">回答：原话</p>'
            '<p id="p1"><span text-color="rgb(100,37,208)">建议：旧建议一</span></p>'
            '<p id="p2"><span text-color="rgb(100,37,208)">参考回答：旧口述二</span></p>'
            '<figure id="img1"><source token="diagram"/></figure></root>'
        )
        p = {'document': 'TestDocument', 'revision': 4, 'operations': [{
            'command': 'block_replace',
            'start_block_id': 'p1',
            'end_block_id': 'p2',
            'expected_texts': ['建议：旧建议一', '参考回答：旧口述二'],
            'content': xml('建议：听了一下录音，这里直接说排查步骤') + xml('参考回答：先查供电，再看时钟'),
        }]}
        self.assertTrue(gate.check(p)['passed'])
        summary = self.run_publish(p, fake=fake)
        self.assertTrue(summary['passed'])
        self.assertEqual([gate.text(n) for n in fake.root[:4]], [
            'Q1', '回答：原话', '建议：听了一下录音，这里直接说排查步骤', '参考回答：先查供电，再看时钟'
        ])
        self.assertIsNotNone(next(n for n in fake.root if n.get('id') == 'img1').find('source'))

        # Range spanning non-advice block must be rejected before any write
        bad_fake = FakeLark()
        bad_fake.root = ET.fromstring(
            '<root><p id="a1">回答：原话</p>'
            '<p id="p1"><span text-color="rgb(100,37,208)">建议：旧建议</span></p></root>'
        )
        bad_p = {'document': 'TestDocument', 'revision': 4, 'operations': [{
            'command': 'block_replace',
            'start_block_id': 'a1',
            'end_block_id': 'p1',
            'expected_texts': ['回答：原话', '建议：旧建议'],
            'content': xml('建议：新建议'),
        }]}
        with self.assertRaises(gate.GateError):
            self.run_publish(bad_p, fake=bad_fake)
        self.assertEqual(bad_fake.writes, 0)

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
