# 具身大模型研究进展雷达

静态网页 + Python 增量抓取 + GitHub Actions 每日更新。没有模型凭据时不调用付费 LLM，原文提取可独立运行。研究简报见 `docs/第一版看板.md`，网页入口 `site/index.html`。

## 本地查看（macOS / Linux）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/update.py --offline
python -m http.server 8000 --directory site
```

浏览器打开 http://localhost:8000 。不要双击 HTML：浏览器可能禁止从 file:// 读取 JSON。

实际联网更新：

```bash
python scripts/update.py
```

接口失败会保留旧数据并记录状态；全失败时返回非零退出码。arXiv 完整分页后才推进水位；默认首次183天，后续回溯7天按 `lastUpdatedDate` 获取修订。首次命中超过2000条时，增加 `max_pages`（默认上限40页，每页100条）；未完成前不将抓取标为完整。网页“近6个月”按六个日历月计算，覆盖起点与首次抓取183天略有差别。

## 从零部署到 GitHub Pages

1. 在 GitHub 新建一个 **public** 仓库，例如 `embodied-radar`，默认分支为 `main`。公共仓库可使用免费 Pages 与标准托管 Actions；服务额度和政策以 GitHub 为准。
2. 将本项目文件上传到仓库根目录。`.github/workflows/update.yml` 是隐藏目录里的必要文件。可用 GitHub 网页上传或命令行：

```bash
git init
git add .
git commit -m "Initial embodied research radar"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/embodied-radar.git
git push -u origin main
```

3. 仓库 Settings → Actions → General → Workflow permissions 选 **Read and write permissions**，保存。若组织禁止此权限，需要管理员开放。
4. Settings → Pages → Build and deployment → Source 选 **GitHub Actions**。本项目上传 `site/` 为发布目录。
5. Actions → Update research radar and deploy Pages → Run workflow。成功后，Settings → Pages 会显示 `https://YOUR_NAME.github.io/embodied-radar/`。页面资源全部使用相对路径，支持仓库子路径。
6. 默认每天 **Asia/Taipei 09:17**（UTC 01:17）运行。Actions 的 cron 可能延迟，长时间无活动的公共仓库可能停用定时工作流；不是精确计时或实时推送服务。随时可手动 Run workflow。
7. 自动任务自己提交的数据不会触发新的 push 工作流；同一任务直接继续部署。修改 `config/manual.yaml` 等文件并 push 后也会重新抓取和部署。

已实际部署到 https://miaojulin2-byte.github.io/embodied-research-radar/ ，仓库为 https://github.com/miaojulin2-byte/embodied-research-radar 。Pages来源已设为GitHub Actions，首次更新与发布已成功；每日09:17（Asia/Taipei）更新。模型与S2的可选Secrets尚未配置。

## 可选 API 配置

Settings → Secrets and variables → Actions：

| 名称 | 类型 | 用途 |
|---|---|---|
| `GITHUB_TOKEN` | 自动提供 | 仓库元数据读取、提交快照；无需自己添加 |
| `S2_API_KEY` | Secret | Semantic Scholar 配额；留空则尝试公共接口 |
| `LLM_API_KEY` | Secret | 可选分类服务凭据 |
| `LLM_BASE_URL` | Variable | OpenAI-compatible 服务地址，须以 `/v1` 等服务实际前缀结尾 |
| `LLM_MODEL` | Variable | 服务支持的模型名称 |

模型接口已启用凭据检测：`llm.enabled: true` 且配置 `LLM_API_KEY` 后才调用模型，最多30篇/轮。向指定模型发送标题、路线说明及已抓取的论文/项目页文本片段，用于中文摘要、多路线分类与带引文的字段提取。没有 key 时仍生成原文摘要摘录、规则分类和字段证据；只有分类不确定或缺摘要时进入分类复核。模型调用可能收费，模型名应设置为服务实际支持的名称。

LLM 不能创建“已开放权重”“已部署”等证据。机构、本体、数据、评测的模型提取必须带已抓取来源URL与可逐字匹配的引文；机构引文还须来自作者机构区。字段值也必须是引文中的原文片段，拒绝“引文真实但数值/硬件名称另编”的情况。通过后标记“模型提取·引文已核对”，不标成人工核验。地区由论文明确的机构和可维护映射推导，未知映射保留缺失。Semantic Scholar 的作者 affiliation 是当前作者档案，不能直接等同于论文发表时机构。

## 手动录入与审核

编辑 `config/manual.yaml`（已有第一版人工核验记录），新增例如：

```yaml
items:
  - id: lab-project-2026
    title: 待录入的真实工作名称
    published: '2026-10-25'
    url: https://example.org/actual-primary-source
    routes: [R2, R4, R6]
    primary_route: R2
    institution: 按一手来源填写
    region: 国内
    contribution: 按原文提炼一句话贡献
    kind: 技术报告
    hardware: 按原文填写
    data_scale: 未披露
    evaluation: 未披露
    evidence: [report]
    verified: false
    # github: OWNER/REPO
    # aliases: ['arxiv:2601.12345', 'https://lab.example/blog']
```

示例不是研究事实，不能原样标为 verified。正式录入必须使用真实原始链接。`verified: true` 表示人工已检查该条正式字段；仍可把某字段填成“未披露”。`evidence` 可分别填写 `paper / report / code / weights / demo / deployment`。各状态需分别核验。模型卡存在或仓库存在不自动证明权重已发布。权重开放不等同于许可允许商用；另填 `license`。

`region` 建议：国内、海外、国际合作、待核验。跨国工作保留国际合作，不硬分国内外。正式记录要求 `published` 日期及有效路线。

同一工作的多来源合并：arXiv 自动去掉 v1/v2；相同规范URL按ID合并。跨来源需要在 `aliases` 显式写目标记录ID或URL，避免靠相似标题误合并。提供 arXiv URL 或 `arxiv:编号` 作为主ID最稳定。历史已有人工核验的字段不会被自动元数据覆盖。手动配置删条不删除已入库记录；需要清理快照时显式编辑 JSON。

## 新路线、新来源

- 新路线：在 `config/routes.yaml` 加 `id/name/idea/keywords/bottleneck`。前端自动生成列；LLM 读取同一配置，无需改JS。历史关键词条目会重新分类，人工条目需自行调整。
- 重点机构：编辑 `config/institutions.yaml`；名单用于追踪覆盖清单，不用机构名字直接猜论文归属。具体抓取入口仍需加入 sources 的 author/repo/feed。
- 重点仓库：在 `github.repositories` 加 `OWNER/REPO`；在论文人工条目中填 `github` 关联。抓取 star、许可、最近5次 release；release 事件不是论文发布日期。
- Hugging Face：在 `huggingface.authors` 加组织名，抓每组织最近30个模型（可调）。`createdAt` 是模型仓库创建日期，`lastModified` 是仓库更新日期；都不冒充权重首次发布时间。检测权重文件只是线索。受限仓库或列表截断会影响覆盖。
- RSS：在 `rss` 中加 `{name, url, keywords}`。支持 RSS 2.0 与 Atom；官方博客抓到的默认是线索，论文、权重和部署证据仍需审核。初版仅配置已核验 NVIDIA feed；DeepMind/PI 可从官方发布入口人工维护，未编造RSS地址。
- 全新数据源：在 `scripts/update.py` 中编写 fetch 函数，输出同样字段，调用 `merge_items` 并写入来源状态。数据源原始URL保存在 `sources`。

## 指标与边界

- 周新增图：按首发日期统计过去8周，周一开始；多标签可重复计入不同路线，列内卡片只归主路线。
- 引用与 star 记录每天快照。周增必须存在至少7天前、距目标基线不超过2天的记录，且基线与当前观测足够新。未采集或失败显示“待核验”，不填0。
- 本周关注 = max(0, Δ引用) + max(0, Δstar)/100，仅两个信号都存在时计算。可审查的关注度排序，不是质量或路线热度判断。原始信号同时展示；没有一周历史时为空。
- 开源复现数、被用作 baseline 次数需要全文证据，保留人工字段 `replication_count/baseline_count`，不把 API 引用数当成 baseline 次数。
- 未达到抓取上限不保证全领域覆盖；关键词检索会漏中文发布、私有模型及不同术语的论文，也会包含噪声。国内发布优先通过人工录入补充。追踪名单内没有条目不代表没有进展。
- 本仓库不把论文成功率横向混排。不同任务、机器人、数据预算、采样数量不能直接比较。
- 在此对话说“刷新”，可按已保存的快照重新联网核验并标记新增/变化；网页由 Actions 更新，浏览器刷新只重新加载已发布的JSON，不会直接执行抓取。

## 验证

```bash
python -m unittest discover -s tests -v
node --check site/app.js
python scripts/update.py --offline
```

覆盖 arXiv 版本合并、人工字段保留、显式跨来源别名、同名不同工作不误合并、缺失/过期基线、错误Atom响应和多标签关键词审核。联网接入状态可在网页“来源健康”查看。本地未配置模型凭据，实测未调用付费模型；模型接口使用模拟响应验证了引文校验和拒绝无依据事实。

## 目录

```text
.github/workflows/update.yml  每日抓取、提交快照、部署
config/routes.yaml           路线与关键词
config/sources.yaml          数据源、限速、LLM开关
config/institutions.yaml     国内外重点机构
config/manual.yaml           人工记录/审核/跨来源合并
config/milestones.yaml       经典里程碑
config/editorial.yaml        本期精选及推荐理由
scripts/update.py            数据流水线与导出
scripts/evidence.py          原文提取、字段证据、资源检查与可选LLM
config/organizations.yaml    机构别名与地区映射
scripts/build_report.py      重建第001期固定研究简报
site/index.html              交互看板
site/app.js / style.css      交互与样式
site/report.html             第一版研究简报
site/data/dashboard.json     当前快照、指标、历史、来源健康
site/data/papers.csv / .md   数据导出
site/data/research-state.json 对话刷新与审核状态
site/data/source-audit.json  一手链接抽查结果
docs/第一版看板.md            完整研究简报原文
tests/test_update.py         数据契约回归检查
```

API依据：[arXiv API](https://info.arxiv.org/help/api/user-manual.html)、[Semantic Scholar](https://api.semanticscholar.org/api-docs)、[Hugging Face Hub API](https://huggingface.co/docs/hub/en/api)、[GitHub Pages Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。

## AIHOT参考与首期编辑

参考 [AIHOT](https://github.com/KKKKhazix/AIHOT) 的精选/全部分层和事件归并思路。未复制其代码、品牌或信源名单。静态版首页使用 `config/editorial.yaml` 人工指定精选与理由，新增候选不会自动成为精选。规范ID/显式aliases归并一项工作的多来源，首发与修订分别保留；尚未实现自动语义聚簇或双LLM评分。默认路线视图隐藏低置信度候选，可打开“包含待审核候选”；待审核视图始终可见候选。大量匹配时前端先显示部分条目，可用搜索进一步缩小范围，CSV包含全量数据。

规则分类按标题/摘要中的明确方法词加权，强度0–0.85是启发值，不是经校准的概率。Semantic Scholar公共配额遇到429后停止本轮剩余补全，保留历史指标，下次继续；未抓取不会显示为0。第001期报告记录36条人工研究索引，另有自动抓取候选，二者数量不能混用。

前端参考AIHOT的紧凑阅读流：侧栏导航、精选/全部切换、日期分组、原始证据折叠区，以及宽屏右栏关注清单。收藏与深浅外观使用浏览器localStorage，不上传服务器；清除浏览器站点数据会清空收藏。

本机实测已保存约2000条arXiv候选，另有人工索引与RSS线索；完整窗口分页遇到间歇性TLS连接失败，因此尚未推进arXiv完整水位。GitHub三个仓库和HF模型列表已接通，S2公共接口出现429并保留状态。这是本次本地验证结果，不是所有外部API永久可用的保证。

## 自动证据补全（本次新增）

一次日常更新现在按顺序执行：元数据采集 → 全量摘要摘录/多路线规则分类 → 正文补全队列 → 作者链接项目页 → 代码/权重资源验证 → 可选LLM中文摘要与带引文字段提取 → JSON/CSV/Markdown导出。

```bash
# 日常完整更新；GitHub Actions 调用这个入口
python scripts/update.py
# 只处理既有候选，不重复抓整个arXiv窗口
python scripts/update.py --enrich-only --limit 40
# 指定条目实际复核，已处理过的也可以重跑
python scripts/update.py --enrich-only --ids 2610.31670 2610.22342
# 完全离线重建，复用已抓取的正文证据
python scripts/update.py --offline
```

`config/sources.yaml` 的 `extraction` 默认开启，每轮处理40篇。队列优先处理未提取、论文已修订或到期刷新条目；失败条目次日重试，`--ids` 可手动强制重试。HTML优先，无HTML或未提取到机构时读取PDF；PDF默认最多12页、20MB，可调整。第一期的约2000篇历史候选需要多轮补全，不会一次抓完所有全文。程序保留每篇处理进度，后续继续；当前仓库Actions已启用；历史队列由backfill.yml持续分批推进，纯本地副本仍须手动执行或使用已部署工作流。

机构取自明确作者机构区域，参考文献和正文提及的机构不作为作者归属。映射外的明确机构保留原文，不猜地区。原文摘录保持原语言，不冒充中文翻译。模型未配置时仍可完整运行免费流程；配置模型后可获得中文摘要和更细的方法分类。原文摘录、规则推断、模型引文匹配均不是独立复现实验。

`field_evidence` 为每个字段保存 `value/status/source_url/quote/method/checked_at`：

| 状态 | 页面含义 |
|---|---|
| `human` | 人工核验过的字段 |
| `supported` | 从原文明确区域/陈述中提取 |
| `derived` | 根据原文和规则推导，例如机构地区映射 |
| `llm_grounded` | 模型提取，引用来源和原文片段已匹配 |
| `candidate` | 有未核验线索，尚未补到证据 |
| `missing` | 还没获取对应证据 |
| `not_found` | 已处理来源，本轮未提取到该字段；不等于原文未披露 |
| `fetch_failed` | 对应来源抓取失败，保留重试 |

`review` 现在只表示分类置信不足或缺少摘要；字段缺失由 `missing_fields` 和证据状态单独表示。前端“正文已处理”表示已抓取并扫描来源，不表示七个字段都已补齐，也不表示人工审核通过。

代码开放须来自作者关联链接且通过公开仓库及实现语言检查；权重开放须存在权重文件、非私有/受限并且文件HEAD访问成功。项目页有一个按钮、模型卡存在、仓库star变化都不会自动证明权重开放或商业部署。商业部署仍保留明确的一手证据/人工记录，程序不从演示视频推断。

正文缓存位于 `.cache/evidence/`，不提交也不发布原文全文；GitHub Actions使用缓存复用下载。公开JSON只保留所需字段、短摘录和来源链接。新增机构别名编辑 `config/organizations.yaml`；新增路线仍编辑 `config/routes.yaml`。

前端可按人工核验、自动整理、分类需复核、正文已处理/待补全/失败筛选。自动提取到的机构会进入机构筛选；每张卡片展开“证据与数据”可逐字段检查来源。代码、权重检查单独展示，不混入模型分类置信度。

验证包含26项检查：来源解析、明确机构区与参考文献隔离、地区映射、修订缓存失效、模型伪造引文拒绝、模型卡不足以证明权重开放，以及既有去重和增速基线检查。模型摘要端到端的真实调用仍需配置用户自己的模型服务后验证。

## 已部署服务与持续补全

- 站点：https://miaojulin2-byte.github.io/embodied-research-radar/
- 仓库：https://github.com/miaojulin2-byte/embodied-research-radar
- 每日更新：`Daily update and Pages`，Asia/Taipei 09:17。
- 历史补全：`Complete evidence backlog`，每批最多25分钟，每5篇原子保存进度。仍有队列且本批有进展时自动派发下一批；每两小时的第47分钟另有重试巡检。无进展时停止自衔接，避免无限重跑无法获取的来源。
- 即时发布：`Publish current snapshot`，只构建/发布现有数据，不依赖外部抓取接口。
- GitHub Actions并发组保护数据提交；首次源码包只用于初始化，正常维护以仓库已展开的源码为准。
- 首屏使用 `dashboard-home.json`；其他视图加载精简索引，展开卡片时按需读取 `data/items/`。完整 `dashboard.json` 与CSV仍可导出。

初次上线时历史补全仍在运行，不把“任务已启动”写成“全部字段已补齐”。实际数量以线上数据和工作流日志为准；抓取失败和原文未提取到分别保留。
