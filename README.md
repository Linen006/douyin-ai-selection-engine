# 抖音 AI 选品剪辑引擎

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

一个可演示、可解释的短视频电商选品与剪辑 MVP：

```text
导入样例 → 选品评分 → 素材审核 → 人工复核 → ffmpeg 剪辑 → 风险报告
```

## 特点

- 可解释选品：硬性过滤 + 六维评分，每个商品都有通过/淘汰原因
- 素材合规审核：价格、极限词、功效、明星/网红、水印、AB 货规则检测
- 人工在环：不确定项进入人工复核队列，不假装全自动
- 风险报告：成片附带 JSON / Markdown / HTML 三种报告
- 离线可跑：没有 DeepSeek Key 也能用 Mock 模式完整演示
- 中英切换：Web 界面支持中文 / English
- Agent Skill：提供 `SKILL.md`，可作为 Codex / Claude Skill 安装

## 技术栈

Python 3.12、Flask、SQLite、DeepSeek API、ffmpeg、HTML/CSS/JS、pytest。

## 快速开始

```powershell
git clone https://github.com/Linen006/douyin-ai-selection-engine.git
cd douyin-ai-selection-engine
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.cli demo
```

Windows 下 `ffmpeg` 是可选的：项目会优先使用系统 `ffmpeg`，找不到时回退到 `imageio-ffmpeg` 自带的 ffmpeg。

## CLI

| 命令 | 作用 |
| --- | --- |
| `python -m app.cli demo` | 一键跑通全部流程 |
| `python -m app.cli score` | 只跑选品评分 |
| `python -m app.cli audit` | 只跑素材审核 |
| `python -m app.cli review list` | 查看待人工复核 |
| `python -m app.cli review approve --task-id 1` | 通过复核 |
| `python -m app.cli review reject --task-id 1` | 淘汰复核 |
| `python -m app.cli edit` | 从已通过素材生成成片 |
| `python -m app.cli report` | 生成风险报告 |
| `python -m app.cli web` | 启动 Web 界面 |
| `python -m pytest -q` | 运行测试 |

## Web 界面

启动 `python -m app.cli web` 后访问：

- `/` 工作台
- `/products` 商品选品评分
- `/materials` 素材合规审核
- `/jobs` 剪辑任务
- `/reports` 风险报告

## AI 模式

默认 Mock 模式，无需 API Key。创建 `.env` 并配置 `DEEPSEEK_API_KEY` 后，人工复核任务会附带 DeepSeek 建议；网络不可用时自动降级。`.env` 已被 `.gitignore` 忽略。

## 项目结构

```text
app/            核心代码
  scoring.py    选品评分
  audit.py      素材审核
  review.py     人工复核
  editor.py     ffmpeg 剪辑
  report.py     风险报告
  ai.py         DeepSeek + Mock
data/sample/    样例数据
tests/          自动化测试
docs/           项目方案与同类对比
```

## 同类项目对比

多数项目只做通用剪辑或只做选品分析。本项目把选品、合规、复核、剪辑、报告串成闭环。详见 [docs/COMPARISON.md](docs/COMPARISON.md)。

## 测试

```powershell
python -m pytest -q
```

测试覆盖：数据库建表、样例导入、评分规则、审核规则、人工复核、剪辑和报告生成。

## Agent Skill

项目根目录的 [SKILL.md](SKILL.md) 可作为 Codex / Claude 等 Agent 的 Skill 安装，用自然语言驱动流程。

## License

[MIT](LICENSE)
