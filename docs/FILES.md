# 文件说明

本文件列出仓库中每个文件的用途，方便快速定位和阅读。

## 根目录

| 文件 | 说明 |
| --- | --- |
| `README.md` | 项目简介、快速开始、功能、命令、截图和 License |
| `SKILL.md` | Agent Skill 入口，供 Codex/Claude 等工具调用 |
| `LICENSE` | MIT 开源协议 |
| `requirements.txt` | Python 依赖清单 |
| `pytest.ini` | pytest 测试配置 |
| `.env.example` | DeepSeek Key 配置模板，复制为 `.env` 使用 |
| `.gitignore` | 忽略虚拟环境、密钥、数据库和生成产物 |
| `.github/workflows/tests.yml` | GitHub Actions 自动测试流程 |

## app

| 文件 | 说明 |
| --- | --- |
| `app/cli.py` | 命令行入口，`demo/score/audit/review/edit/report/web` |
| `app/config.py` | 路径与运行时配置，读取 `.env` |
| `app/db.py` | SQLite 连接与建表 |
| `app/schema.sql` | 8 张数据库表结构 |
| `app/seed.py` | 导入样例商品和素材 |
| `app/scoring.py` | 选品评分：硬性过滤 + 六维打分 |
| `app/audit.py` | 素材合规审核规则 |
| `app/review.py` | 人工复核队列 |
| `app/editor.py` | ffmpeg 自动剪辑 |
| `app/report.py` | 生成 JSON/MD/HTML 风险报告 |
| `app/ai.py` | DeepSeek 调用与 Mock 降级 |
| `app/ffmpeg.py` | 自动查找系统或内置 ffmpeg |
| `app/media.py` | 生成合成测试视频 |
| `app/web.py` | Web 页面路由 |
| `app/i18n.py` | 中英文文案 |
| `app/templates/` | 网页模板：工作台、评分、审核、剪辑、报告 |

## data

| 文件 | 说明 |
| --- | --- |
| `data/sample/products.json` | 样例商品 |
| `data/sample/materials.json` | 样例素材和口播文本 |
| `data/demo/media/` | 自动生成的合成测试视频，不提交 |
| `data/demo.db` | 本地 SQLite 数据库，不提交 |
| `data/output/` | 成片与风险报告，不提交 |

## docs

| 文件 | 说明 |
| --- | --- |
| `docs/project-plan.md` | 项目方案：定位、模块、数据表、里程碑 |
| `docs/COMPARISON.md` | 同类项目对比 |
| `docs/FILES.md` | 本文件 |

## tests

| 文件 | 说明 |
| --- | --- |
| `tests/test_smoke.py` | 数据库、样例数据、ffmpeg 发现 |
| `tests/test_scoring.py` | 选品评分规则 |
| `tests/test_audit.py` | 素材审核和人工复核 |
| `tests/test_editor.py` | 剪辑和报告生成 |
