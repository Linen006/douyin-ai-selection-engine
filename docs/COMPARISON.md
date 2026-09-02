# 同类项目对比

调研时间：2026-09-02

## 最相关的项目

| 项目 | 星标 | 链接 | 与本项目的区别 |
| --- | --- | --- | --- |
| short-video-factory | 5264 | https://github.com/YILS-LIN/short-video-factory | 通用短视频工厂，无选品、无合规审核、无人工复核 |
| eCommerce-Skills | 845 | https://github.com/nexscope-ai/eCommerce-Skills | 亚马逊/Shopify 电商 Skill，缺少抖音素材剪辑闭环 |
| amazon-sorftime-research-MCP-skill | 802 | https://github.com/liangdabiao/amazon-sorftime-research-MCP-skill | 专业选品分析，绑定亚马逊数据，无剪辑与审核 |
| story-ai-cutting | 50 | https://github.com/elvisNg/story-ai-cutting | 剪辑管线清晰，但无选品、审核、报告 |
| merchant-agent | 49 | https://github.com/yyf2002-oos/merchant-agent | 电商全流程 Agent，偏自动化，不是可演示作品集 |
| pdd-douyin-system | 21 | https://github.com/CT6668/pdd-douyin-system | 最接近“选品+素材+看板”，但无视频剪辑、素材审核、人工复核、风险报告 |
| codex-tiktok-video-factory | 14 | https://github.com/yongyingZou/codex-tiktok-video-factory | 带货素材到成片很扎实，但无选品评分，形态是 Codex Skill |

## 本项目的差异化

1. 可解释选品打分：硬性过滤 + 六维评分，每个结果都有原因。
2. 素材合规审核：价格、极限词、功效、明星/网红、水印、AB 货规则。
3. 人工复核节点：不确定项必须人工确认。
4. 风险报告 + 删除记录：成片附带删了什么、为什么删。
5. 离线 Mock + 真实 DeepSeek 双模式：没有 Key 也能演示。
6. 中文展示包 + 中英 Web 切换：适合面试现场打开给 HR 看。
7. 可作为 Agent Skill 使用：提供 `SKILL.md`。

## 借鉴来源

- 多维评分模型：借鉴 `amazon-sorftime-research-MCP-skill` 的多维评分思路。
- 剪辑中间产物：借鉴 `story-ai-cutting` 的“分割 → 理解 → 编排 → 合成”结构。
- Skill 打包方式：借鉴 `eCommerce-Skills` 的 `SKILL.md` + 薄脚本形态。
