# 项目事实与维护入口

本项目为具身研究静态看板，用户要求 Python + JSON + GitHub Actions + GitHub Pages，可免费部署；不要用需常驻后端的框架替换此默认路线。

- 正式抓取入口：`scripts/update.py`；配置契约和部署步骤：`README.md`。
- 首期人工研究索引：`config/manual.yaml`，经典：`config/milestones.yaml`，精选：`config/editorial.yaml`。
- 抓取快照：`site/data/dashboard.json`；逐源状态 `sources`，arXiv只有完整分页后才能推进 `arxiv_cursor`。
- 对话人工检索水位：`site/data/research-state.json`。不能用自动接口水位替代人工研究水位。
- 首期完整报告：`docs/第一版看板.md`；生成器 `scripts/build_report.py` 固定为第001期，日常抓取不重写研究判断。
- 原始网页抽查记录：`site/data/source-audit.json`；该记录不表示指标已独立复现。
- 已创建公开仓库 `miaojulin2-byte/embodied-research-radar`，Pages已启用，首次每日更新与发布成功。站点 `https://miaojulin2-byte.github.io/embodied-research-radar/`。可选LLM/S2 Secrets未配置。
- 各证据状态必须分别核验；权重文件线索、模型卡、API可用、预告与商用部署不能互相替代。
- 低置信度保留审核，机构/国别不能根据作者姓名猜测。跨国合作保留独立地区值。
- 初版参考AIHOT的精选/全部分层与事件来源归并思路，未移植其后端或复制品牌。

验证：`.venv/bin/python -m unittest discover -s tests -v`；`node --check site/app.js`。本地预览：`python3 -m http.server 8000 --bind 127.0.0.1 --directory site`。

## 自动证据流水线

- `scripts/evidence.py` 为自动摘要摘录、正文/PDF/作者项目页、字段证据和资源验证入口，已接入 `update.py` 日常任务。
- `config/organizations.yaml` 维护明确机构别名与地区映射；不在正文/参考文献中猜作者机构。
- `--enrich-only --limit 40` 可独立推进历史候选；`--ids` 强制处理指定条目；`--offline` 复用已下载证据。
- `field_evidence` 的状态区分人工核验、原文提取、规则推断、模型引文匹配、未获取、未提取到和抓取失败。`review` 只表示分类/摘要需要复核，不等于所有缺字段都要人工确认。
- 没有模型凭据时使用免费原文摘录与规则提取。LLM中文摘要和语义分类接口已接入，但本地尚无凭据，不能宣称已实际调用验证。
- 正文按每轮预算补全；“正文已处理”不表示字段齐全。`.cache/evidence/` 仅本地/Actions缓存，不发布全文。

- 本次实测与验证统计见 `site/data/enrichment-audit.json`；首次正文补全已处理50篇，后续以实时快照为准。

## 云端运行状态与前端载荷

- `.github/workflows/update.yml` 每日 Asia/Taipei 09:17 更新并发布。
- `.github/workflows/backfill.yml` 分批补全剩余正文，每25分钟以内结束一批；每5篇保存快照，有进展时自动衔接下一批。每两小时第47分钟重试巡检，队列为0时跳过。
- `.github/workflows/publish.yml` 独立发布已有快照；仓库和Pages均已启用，不要再用“尚未部署”的旧口径。
- `scripts/site_data.py` 生成首屏、索引和逐条证据JSON，避免首屏下载完整历史数据；完整数据仍保留。
- 本地快照和云端数据可能不同步。生产状态以GitHub仓库默认分支、Actions运行结果及公开站点为准。
