from pathlib import Path
import json,yaml,html,re
root=Path(__file__).resolve().parents[1]
rows=yaml.safe_load((root/'config/manual.yaml').read_text())['items']+yaml.safe_load((root/'config/milestones.yaml').read_text())['items']
routes=yaml.safe_load((root/'config/routes.yaml').read_text())
link=lambda x:f"[{x['title']}]({x['url']})"
parts=['''# 国内外具身大模型研究进展看板 · 第001期

## 0. 看板元信息

- 更新基准：2026-10-25，Asia/Taipei。本期为首次建立基线，所有收录可视为 🆕；后续刷新仅标新增与变化。
- 重点首发窗口：2026-04-25—2026-10-25；首发日期与修订日期分列。窗口外参照明确标注，经典工作进入里程碑。
- 本期人工索引36条，覆盖11条路线。arXiv摘要/HTML、团队项目页、官方研究博客为主要证据；不把媒体当唯一依据。联网搜索使用 agent-reach / Exa，另用页面读取交叉核验。
- 原始链接均保留；G0.5、GE-Act 2.0、ROVE、X2Real、EBench、Labimus、DexJoCo-X及5条经典里程碑做了二次页面核对。Spark-0与RL-Co的机构尚待核验。
- 接口实测的逐源成功/失败状态保存在网页“来源健康”和JSON中。未建立完整 arXiv 水位时，不能把手工精选数量当作该领域总产出；没有历史周基线时不计算增速。
- 分类说明：R1—R6主要描述模型/学习方法，R7/R11是横向基础设施，R8—R10描述能力任务；允许重叠，主路线仅决定卡片位置。国别按主要机构所在地记录，跨国联合工作保留“国际合作”。

## 1. 本期头条（Top 5）

1. **自回归动作路线仍在推进。** G0.5（2026-08-12）统一推理与动作生成，提示连续动作专家尚未形成唯一范式；结果属于作者同协议实验。[论文](https://arxiv.org/abs/2608.11739)
2. **世界动作模型开始检验自己的预训练与扩展规律。** GE-Act 2.0（2026-09-04）从操作数据训练可学习组件，而非只继承现成视频模型；这扩大了R4的设计空间。[技术报告](https://arxiv.org/abs/2609.05588)
3. **家庭泛化的验证粒度提高。** Helix 2.5（2026-09-17）用未见家庭与预训练消融检验迁移，但仍是官方实验，不能推广为任意家庭自治。[官方结果](https://www.figure.ai/news/helix-2-5-zero-shot-30-home-generalization)
4. **全身控制与高层推理更紧密结合。** Gemini Robotics 2（2026-07-30）发布全身、灵巧操作及协作能力体系；合作方访问与公开权重是不同状态。[官方发布](https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/)
5. **评测可信度成为基础设施问题。** X2Real（2026-09-23）显式检验仿真与实机得分相关性；对模型选型，协议比单个高分更值得追踪。[论文](https://arxiv.org/abs/2609.27449)

另：Pi API beta于2026-10-13发布，是托管训练/推理产品变化，不能作为一篇新模型论文，也不自动证明API最新模型权重公开。[官方](https://www.pi.website/blog/api-beta)

## 2. 技术路线总览表

“→ 待建立基线”表示暂不判断升降，不表示研究停滞。括号是本期收录中落在窗口内的首发数量，包含论文与官方技术/产品公告；多标签重复计数，不能相加当总论文数。复现数及baseline采用次数未做全文系统统计，保持未知。

| 路线 | 核心思想（≤30字） | 代表工作（含历史参照） | 国内代表 | 海外代表 | 近6个月热度及依据 | 主要瓶颈 |
|---|---|---|---|---|---|---|''']
for r in routes:
    xs=[x for x in rows if r['id'] in x['routes']]
    recent=[x for x in xs if '2026-04-25'<=x['published']<='2026-10-25']
    reps=sorted(xs,key=lambda x:x['published'],reverse=True)[:5]
    domestic=list(dict.fromkeys(x['institution'] for x in xs if x['region']=='国内'))[:2]
    overseas=list(dict.fromkeys(x['institution'] for x in xs if x['region']=='海外'))[:2]
    parts.append(f"| {r['id']} {r['name']} | {r['idea']} | {'、'.join(link(x) for x in reps)} | {' / '.join(domestic) or '本轮待补'} | {' / '.join(overseas) or '本轮待补'} | → 待建立基线（收录{len(recent)}项新首发） | {r['bottleneck']} |")
parts.append('''
## 3. 各路线详细卡片

日期为原始论文/所链接官方发布的首发日期；“修订”单独标明。所有数值均为作者或公司报告，只能在对应协议下理解。“论文发布”“代码开放”“权重开放”“演示”“官方报告部署”是独立事实；未填的状态一律未确认。官方报告部署不等于已独立验证或已商业规模复制。类型为计划/产品/博客的记录不计为论文。
''')
labels={'paper':'论文已发布','report':'报告/官方技术文','code':'代码开放','weights':'权重开放','demo':'演示','deployment':'官方报告实际部署'}
for r in routes:
    parts.append(f"\n### {r['id']}. {r['name']}\n\n| 名称 | 机构 | 国别/地区 | 发布日期 | 类型 | 关键创新（≤40字） | 本体/硬件 | 数据规模 | 关键指标或评测 | 开源/证据状态 | 链接 |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for x in sorted([x for x in rows if r['id'] in x['routes']],key=lambda x:x['published'],reverse=True):
        date=x['published']+('（窗口外）' if x['published']<'2026-04-25' else '')
        if x.get('updated'):date+='；修订'+x['updated'][:10]
        states='、'.join(labels[e] for e in x.get('evidence',[]))
        if 'weights' not in x.get('evidence',[]):states+='；权重未核验'
        if not x.get('verified'):states+='；机构等待核验'
        parts.append('| '+' | '.join(str(v).replace('|','/') for v in [x['title'],x['institution'],x['region'],date,x['kind'],x['contribution'],x.get('hardware','未核验'),x.get('data_scale','未核验'),x.get('evaluation','未填未核验指标'),states,link(x)])+' |')
parts.append('''
## 4. 国内 vs 海外对比

这是一组有出处的样本对照，不是国家总体实力排名；披露粒度、硬件、任务和预算差异过大，不能给出统一领先结论。

| 维度 | 国内证据 | 海外证据 | 可支持的判断与边界 |
|---|---|---|---|
| 模型架构 | [G0.5，2026-08-12](https://arxiv.org/abs/2608.11739)为统一自回归；[GE-Act 2.0，2026-09-04](https://arxiv.org/abs/2609.05588)为WAM | [DreamZero，2026-02-17](https://arxiv.org/abs/2602.15922)为视频动作联合生成；[Helix 02，2026-01-27](https://www.figure.ai/news/helix-02)为分层控制 | 两边均有多种架构；没有证据支持按国别划分单一路线 |
| 数据积累 | [GE-Act 2.0](https://arxiv.org/abs/2609.05588)报告操作共训练扩展；[ZETA，2026-09-02](https://arxiv.org/abs/2609.02546)检验预训练本体覆盖 | [Index，2026-08-25](https://www.figure.ai/news/introducing-index)为专属人类行为采集；[V-JEPA 2，2025-06-11](https://ai.meta.com/research/publications/v-jepa-2-self-supervised-video-models-enable-understanding-prediction-and-planning/)为视频预训练 | 数据口径分别是小时、视频条数、机器人轨迹；不能直接比较规模或质量 |
| 硬件本体 | [ViLoMan，2026-09-16](https://arxiv.org/abs/2609.19340)及[PGMT，2026-09-08](https://arxiv.org/abs/2609.08511)使用G1 | [Gemini Robotics 2](https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/)展示多本体；[Helix 2.5](https://www.figure.ai/news/helix-2-5-zero-shot-30-home-generalization)绑定Figure体系 | 本体多样性与特定硬件深度整合各有优势；硬件产地不能代替算法机构归属 |
| 开源生态 | [RLinf-VLA，2025-10-08；2026-08-12修订](https://arxiv.org/abs/2510.06710)及[代码](https://github.com/RLinf/RLinf)，为中外合作 | [OpenVLA，2024-06-13](https://arxiv.org/abs/2406.09246)公开模型/代码；V-JEPA 2有[官方开放证据](https://ai.meta.com/blog/v-jepa-2-world-model-benchmarks/) | 论文、代码与权重开放必须分开核对；本期没有系统下载/许可审计，不比较开源比例 |
| 商业落地 | 本期国内新论文不构成商用证明；智元等量产/订单信息需另查合同与客户一手材料 | [Pi API beta，2026-10-13](https://www.pi.website/blog/api-beta)报告商业场景合作与实际部署 | 海外样本有产品/部署叙述，仍不能推出整体规模领先；视频、early access、beta和付费部署不等价 |

## 5. 里程碑时间线（2022至今）

| 日期 | 工作 | 范式意义 |
|---|---|---|
| 2022-12-13 | [RT-1](https://arxiv.org/abs/2212.06817) | 大规模真实机器人数据与Transformer策略结合 |
| 2023-07-28 | [RT-2](https://arxiv.org/abs/2307.15818) | 把动作表示为token，迁移视觉语言知识 |
| 2023-10-13 | [Open X-Embodiment](https://arxiv.org/abs/2310.08864) | 跨机构与跨本体数据协作成为基础设施 |
| 2024-02-15 | [UMI](https://arxiv.org/abs/2402.10329) | 手持工具与可迁移演示降低采集门槛 |
| 2024-06-13 | [OpenVLA](https://arxiv.org/abs/2406.09246) | 开放VLA模型与适配工具便于复现 |
| 2024-10-31 | [π0](https://arxiv.org/abs/2410.24164) | 流匹配动作专家推动连续动作生成 |
| 2025-02-20 | [Helix](https://www.figure.ai/news/helix) | 双系统连接语义理解与高频控制 |
| 2025-06-11 | [V-JEPA 2](https://ai.meta.com/research/publications/v-jepa-2-self-supervised-video-models-enable-understanding-prediction-and-planning/) | 自监督视频表征与少量动作适配连接规划 |
| 2026-02-17 | [DreamZero](https://arxiv.org/abs/2602.15922) | 视频与动作联合预测展示WAM控制路径 |
| 2026-07-30 | [Gemini Robotics 2](https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/) | 具身模型延伸到全身与协作控制 |
| 2026-08-12 | [G0.5](https://arxiv.org/abs/2608.11739) | 原生自回归推理与动作联合推进 |
| 2026-09-04 | [GE-Act 2.0](https://arxiv.org/abs/2609.05588) | 从操作数据检验WAM预训练与扩展 |

2026条目是本期观察到的候选转折点，历史地位尚需后续复现与采用验证。

## 6. 趋势判断与争议

以下是基于已核验样本的研究判断，不是完整文献计量结果。

1. **连续动作生成与离散动作会继续并存。** 支持：[π0，2024-10-31](https://arxiv.org/abs/2410.24164)和[DreamZero，2026-02-17](https://arxiv.org/abs/2602.15922)展示连续生成路径。反例：[G0.5，2026-08-12](https://arxiv.org/abs/2608.11739)仍能用统一自回归取得有竞争力的结果。下一步比较应控制预训练数据与推理预算。
2. **WAM会出现多种实现，不能等同于视频生成大模型。** 支持：[GE-Act 2.0，2026-09-04](https://arxiv.org/abs/2609.05588)将压缩、规划与逆动力学组合；[NVIDIA综述，2026-06-15](https://developer.nvidia.com/blog/?p=117282)整理多种路径。反例/约束：[1XWM，2026-01-12](https://www.1x.tech/discover/world-model-self-learning)披露的生成耗时说明控制延迟仍需逐系统验证。
3. **人类视频数据的价值上升，但机器人交互数据仍是关键适配环节。** 支持：[Index，2026-08-25](https://www.figure.ai/news/introducing-index)与[Helix 2.5，2026-09-17](https://www.figure.ai/news/helix-2-5-zero-shot-30-home-generalization)提供预训练迁移证据。反例/约束：[V-JEPA 2，2025-06-11](https://ai.meta.com/research/publications/v-jepa-2-self-supervised-video-models-enable-understanding-prediction-and-planning/)仍需要动作条件后训练，不能据此主张纯视频已经替代机器人数据。
4. **评测将从单一成功率转为协议与能力诊断。** 支持：[EBench，2026-06-16](https://arxiv.org/abs/2606.18239)、[ZETA，2026-09-02](https://arxiv.org/abs/2609.02546)分别检验能力差异与本体泄漏。反例/约束：[Labimus，2026-06-30](https://arxiv.org/abs/2606.31037)表明单纯任务完成仍不足以证明实验精度；更多维度也不自动等于真实部署有效。
5. **RL后训练会与人类干预、仿真和监督锚定混合。** 支持：[ROVE，2026-06-15](https://arxiv.org/abs/2606.17011)使用不完美干预与价值估计；[RL-Co，2026-02-13；10-22修订](https://arxiv.org/abs/2602.12628)结合仿真RL和真实监督。反例/约束：[RLT，2026-03-19](https://www.pi.website/research/rlt)主要针对精细操作阶段，不能据局部改进推出开放世界持续自学已解决。

| 争论 | 一方依据 | 另一方依据 | 应怎样验证 |
|---|---|---|---|
| VLA vs 世界模型 | [G0.5](https://arxiv.org/abs/2608.11739)：直接共享推理与动作参数，接口简洁 | [DreamZero](https://arxiv.org/abs/2602.15922)：联合未来状态与动作帮助迁移 | 同数据/同任务/同本体比较闭环成功率、恢复能力、延迟与推理成本；二者可混合 |
| 真实数据 vs 仿真/视频 | [ZETA](https://arxiv.org/abs/2609.02546)：本体覆盖影响迁移 | [Index](https://www.figure.ai/news/introducing-index)、[X2Real](https://arxiv.org/abs/2609.27449)：可扩展数据与可信仿真评测 | 固定真实数据预算，做来源消融和严格未见本体测试 |
| 端到端 vs 分层 | [G0.5](https://arxiv.org/abs/2608.11739)：统一生成减少独立模块 | [Helix 02](https://www.figure.ai/news/helix-02)：不同时间尺度分层实现高频控制 | 测长期误差积累、层间故障恢复与控制稳定性；不要只按网络模块数量定义端到端 |

## 7. 待核验与下期关注

| 项目 | 已知事实 | 待核验行动 |
|---|---|---|
| [Spark-0，2026-10-15](https://arxiv.org/abs/2610.22342) | 论文可查 | PDF机构、数据/权重下载、许可及部署输入条件 |
| [RL-Co，2026-02-13](https://arxiv.org/abs/2602.12628) | 有窗内修订 | 全部机构、代码/权重、增益百分数的精确定义 |
| [G0.5](https://opengalaxea.github.io/G05/)、[GE-Act 2.0](https://ge-act-v2.github.io/) | 论文及项目入口可查 | 权重真实可下载、许可、复现结果，不根据项目页按钮猜测 |
| [GR00T N2预告，2026-03-16](https://nvidianews.nvidia.com/news/nvidia-expands-open-model-families-to-power-the-next-wave-of-agentic-physical-and-healthcare-ai) | 官方曾预告后续模型 | 检查正式发布、检查点和模型卡；不把预告改写为已开放 |
| 腾讯Robotics X、华为、优必选、宇树自主模型团队、字节Seed、阿里达摩院、上海交大、MIT、TRI等 | 已列入追踪名单 | 补查近六月一手发布；未检索到不代表无进展 |
| Tesla Optimus、Meta新机器人模型 | 本轮没有充分核验的窗内新技术报告 | 区分公开报告、演示、展会、客户部署与第三方验证 |
| 研究量化热度 | 第一版没有完整历史数据 | 至少积累一周快照；另补复现与baseline引用语境，不用总引用代替 |

### 刷新与维护契约

- “刷新”：读取 `site/data/research-state.json` 的上次人工检索日期和索引；检索此后首发及旧条目状态变化。新作 🆕，修订/开放/部署等变化 ✏️。保留旧记录和日期依据。API抓取另有自己的 `arxiv_cursor`，两种水位不能混用。
- “深挖 Rx”：按路线给方法谱系、同协议对比、入门→进阶必读列表；跨路线标签仍保留。
- “对比 A vs B”：逐项比较架构、数据、本体、评测协议、权重许可与局限，未披露项不补猜测。
- “导出”：现有CSV与Markdown在 `site/data/`；全文本报告本身就是Markdown。

### 结合 AIHOT 的调整

参考[AIHOT开源仓库](https://github.com/KKKKhazix/AIHOT)及[实际首页](https://aihot.news/)的“精选/全部”分层与事件归并思路。本项目首页已加入人工精选及推荐理由，用规范ID/显式别名归并来源，保留原始链接和首发/修订时间。没有采用其品牌或复制其代码；完整后端、自动双评分和语义聚簇不属于这版静态项目。新论文不会未经审核自动替换编辑头条。
''')
text='\n'.join(parts)+'\n'
(root/'docs/第一版看板.md').write_text(text)
# Render a conservative Markdown subset into a standalone report; no scripts or remote assets.
def inline(s):
 s=html.escape(s)
 s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<a href="\2" target="_blank" rel="noopener">\1 ↗</a>',s)
 s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
 s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 return s
out=[];table=False
for line in text.splitlines():
 if line.startswith('|'):
  if re.match(r'^\|[\s:|\-]+\|$',line):continue
  if not table:out.append('<div class="tablewrap"><table>');table=True
  out.append('<tr>'+''.join('<td>'+inline(c.strip())+'</td>' for c in line.strip('|').split('|'))+'</tr>')
  continue
 if table:out.append('</table></div>');table=False
 if line.startswith('#'):
  n=len(line)-len(line.lstrip('#'));out.append(f'<h{n}>'+inline(line[n:].strip())+f'</h{n}>')
 elif line.strip():out.append('<p>'+inline(line)+'</p>')
if table:out.append('</table></div>')
(root/'site/report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>第001期研究简报</title><link rel="stylesheet" href="style.css"><style>article{max-width:1400px;margin:40px auto;padding:0 24px}h1{font-size:36px}h2{margin-top:48px}h3{margin-top:30px}p{max-width:1000px}table{border-collapse:collapse;min-width:100%;font-size:12px}td{border:1px solid #d9dfd5;padding:10px;min-width:120px;vertical-align:top}tr:first-child{background:#e6eedc;font-weight:bold}.tablewrap{overflow:auto}code{background:#e6eedc;padding:2px 4px}</style><article><a href="index.html">← 返回交互看板</a>'+''.join(out)+'</article></html>')
state={'last_manual_search_date':'2026-10-25','timezone':'Asia/Taipei','primary_window_start':'2026-04-25','indexed_urls':[x['url'] for x in rows],'known_gaps':['API完整水位未建立时覆盖不足','低置信度及未核验机构保留审核','无一周有效历史时不计算增速'],'version':1}
(root/'site/data/research-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('report',len(rows),'records',len(text),'chars')
