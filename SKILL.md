---
name: douyin-ai-selection-engine
description: Douyin AI product selection, material compliance audit, human review, ffmpeg editing, and risk reports. Use when the user wants to run, test, or extend a demo pipeline for short-video e-commerce product selection and editing.
---

# 抖音 AI 选品剪辑引擎

把需求文档转成一条可演示闭环：

```text
导入样例 → 选品评分 → 素材审核 → 人工复核 → ffmpeg 剪辑 → 风险报告
```

## 快速开始

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.cli demo
```

## 常用命令

```powershell
python -m app.cli demo
python -m app.cli score
python -m app.cli audit
python -m app.cli review list
python -m app.cli edit
python -m app.cli report
python -m app.cli web
python -m pytest -q
```

## 关键模块

- `app/scoring.py` 可解释选品评分
- `app/audit.py` 素材合规审核
- `app/review.py` 人工复核
- `app/editor.py` ffmpeg 剪辑
- `app/report.py` 风险报告
- `app/ai.py` DeepSeek + Mock 双模式

详见 `README.md`、`docs/project-plan.md`、`docs/COMPARISON.md`。
