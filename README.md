# 内容任务规划 Agent（项目二）

帮助运营人员依据主题、预算与截止时间检索素材、估算成本、生成合成脚本并保存内容活动方案。Python 原生实现，无 Agent 框架和第三方运行依赖。真实模型默认推荐已验收的 DeepSeek 提供者，另提供离线 Mock。

## 环境与评审入口

Python 3.9+，在本目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tests/run_examples.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m content_agent examples/request.json --provider mock
```

输入 JSON 包含 request_id、theme、非负整数 budget、带时区的 deadline。CLI 默认把请求记录和方案存入 runtime/plans.db；相同请求复用结果，不同内容复用同一ID将报冲突。失败恢复追加 --resume。使用新数据库可进行全新运行。pyproject.toml 是可选安装配置，直接运行无需安装。

## 真实模型

本地设置 DEEPSEEK_API_KEY，默认地址 https://api.deepseek.com，模型 deepseek-flash。可用 DEEPSEEK_BASE_URL、DEEPSEEK_MODEL 覆盖，或在项目外 ~/.config/content-planning-agent/deepseek.json 配置 base_url、model、api_key（权限600）。.env.example 只提供字段说明，不自动加载。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m content_agent examples/request.json --provider deepseek --database runtime/deepseek-plans.db
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tests/run_deepseek_examples.py
```

真实模型测试会消耗账号额度。证据位于 examples/deepseek；离线证据位于 examples 根目录。其他可选模式：model 使用 OpenAI Responses API（OPENAI_API_KEY、OPENAI_MODEL）；codex 使用本机 CLI 登录；gemini 使用项目外配置或 GEMINI_BASE_URL、GEMINI_MODEL、GEMINI_API_KEY。后两种存在历史兼容/网关错误，不作为当前主要验收路径。

## 输出与限制

输出包含任务步骤及依赖骨架、步骤状态、工具结果、实际模拟费用、估算总额、保存方案和未完成原因，以及模型动作/参数/结果/简要依据的 Trace。保存方案含主题、目标、脚本、素材来源、预算、费用和步骤结果。不执行真实发布。

业务工具和素材是合成的，生成脚本按素材事实组装；真实模型负责观察结果并选择动作。费用表不是服务报价，API token 费用不计入模拟业务预算。固定时钟案例验证模拟耗时决策；默认CLI同时检查真实流逝时间。数据库为本地单进程事务设计，不保证外部服务副作用恰好一次执行。

## 文档

- [需求](docs/01-requirements.md)
- [方案](docs/02-solution.md)
- [评估](docs/03-evaluation.md)
- [AI 使用](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)
- [提交清单](docs/submission-checklist.md)

按用户选择，本次仅交付本地文件夹。考试原规则中的GitHub URL、commit SHA和评审权限未办理；若用于正式考试需另行满足考方要求。用户已确认个人复核贡献；实际用时未完整计时。
