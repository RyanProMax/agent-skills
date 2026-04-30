#!/usr/bin/env python3
"""OPC Idea Miner

Collect public product-idea signals and produce a fixed-template startup product
analysis report for solo builders / one-person-company projects.

The implementation intentionally avoids any paid LLM dependency. It uses public
signals + transparent heuristics so that an agent can call it via CLI and then,
if desired, perform a second LLM polishing pass over the generated report.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus, urljoin

try:
    import requests
    from bs4 import BeautifulSoup
    import yaml
    from jinja2 import Template
except ImportError as exc:  # pragma: no cover - user environment guard
    print(
        f"Missing dependency: {exc}. Install with: pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise

USER_AGENT = (
    "opc-idea-miner/0.1 "
    "(+local research CLI; respect robots/ToS; contact: user-configured)"
)

DEFAULT_CONFIG: Dict[str, Any] = {
    "lookback_days": 30,
    "max_per_source": 25,
    "top_opportunities": 8,
    "output_language": "zh-CN",
    "seed_topics": [
        "ai agent",
        "workflow automation",
        "browser automation",
        "voice agent",
        "llm eval",
        "prompt testing",
        "devtools",
        "chrome extension",
        "accessibility",
        "ecommerce ai",
        "ai search",
        "data extraction",
        "personal productivity",
    ],
    "sources": {
        "hackernews": True,
        "github": True,
        "producthunt": True,
        "devpost": True,
        "yc_rfs": True,
        "gdelt": False,
        "huggingface": True,
    },
    "devpost_galleries": ["https://worldslargesthackathon.devpost.com/project-gallery"],
    "weights": {
        "heat": 0.26,
        "pain": 0.22,
        "opc_fit": 0.22,
        "speed_to_mvp": 0.14,
        "defensibility": 0.10,
        "novelty": 0.06,
    },
    "opc_constraints": {
        "max_mvp_weeks": 4,
        "prefer_b2b": True,
        "prefer_low_regulation": True,
        "avoid": [
            "clinical diagnosis",
            "regulated finance",
            "hardware manufacturing",
            "weapons",
            "crypto trading",
            "gambling",
        ],
    },
}

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "your", "you",
    "are", "can", "will", "build", "built", "using", "use", "uses", "best",
    "top", "new", "tool", "tools", "app", "apps", "product", "project", "open",
    "source", "powered", "based", "simple", "easily", "perfect", "find", "make",
    "making", "create", "creating", "help", "helps", "platform", "system",
}

PAIN_TERMS = {
    "automate", "automation", "reduce", "save", "saves", "saving", "cost",
    "costs", "time", "error", "errors", "manual", "workflow", "workflows",
    "no-show", "no-shows", "confirm", "status", "test", "testing", "eval",
    "compliance", "audit", "hard", "difficult", "lost", "manage", "customer",
    "customers", "support", "invoice", "payments", "inventory", "extract",
    "extraction", "monitor", "monitoring", "triage", "review", "reviewing",
}

SOURCE_WEIGHTS = {
    "yc_rfs": 1.45,
    "producthunt": 1.25,
    "devpost": 1.18,
    "hackernews": 1.08,
    "github": 1.00,
    "huggingface": 0.92,
    "gdelt": 0.85,
    "sample": 0.50,
}

CATEGORY_META: Dict[str, Dict[str, Any]] = {
    "agent_workflow": {
        "title": "垂直工作流 AI Agent：替代人工执行重复服务",
        "keywords": [
            "agent", "agents", "workflow", "automation", "automate", "service",
            "services", "task", "tasks", "ops", "operation", "operations",
            "appointment", "status", "browser", "process", "native",
        ],
        "opc_fit": 8.4,
        "speed_to_mvp": 7.8,
        "defensibility": 7.0,
        "pain_base": 8.1,
        "one_liner": "用一个窄场景 AI Agent 接管客户确认、状态更新、资料整理、表单处理等可重复服务，而不只是给用户一个聊天工具。",
        "target_user": "有大量重复后台任务的小团队：本地服务商、招聘/房产/物流/教育机构、B2B 服务公司。",
        "pain_scenario": "创始人或运营每天在多个系统之间复制信息、提醒客户、更新状态；任务频繁但不足以招聘专人。",
        "why_now": "LLM 工具调用、浏览器自动化和语音/邮件 API 已经足以把单个窄流程做成端到端服务，且 YC 等创业信号正在强调“卖服务而非卖软件”。",
        "mvp_7d": "选一个窄流程，例如预约确认 + Google Sheet/CRM 状态回写，做成可演示脚本。",
        "mvp_14d": "加入人工审核队列、失败重试、日志面板和 2-3 个真实客户测试。",
        "mvp_30d": "产品化为多租户微 SaaS，提供模板化工作流、计费和客户 onboarding。",
        "tech_stack": "Python/FastAPI + Playwright 或 Browserbase + OpenAI/Anthropic 工具调用 + Postgres + Slack/Email/Twilio 集成。",
        "business_model": "按任务量或每席位收费；先做 done-for-you setup fee，再转月费。",
        "risks": "通用 agent 平台竞争强；必须选择足够窄、ROI 可量化、失败风险可控的行业流程。",
        "validation_plan": "找 10 个目标用户访谈，要求他们展示当前 SOP；用半自动脚本替他们跑 1 周，衡量节省小时数与愿付价格。",
    },
    "voice_ops": {
        "title": "AI 语音外呼/预约确认微 SaaS",
        "keywords": [
            "voice", "call", "calls", "phone", "speech", "appointment",
            "appointments", "confirm", "confirmation", "no-show", "no-shows",
            "status", "twilio", "elevenlabs",
        ],
        "opc_fit": 7.6,
        "speed_to_mvp": 7.0,
        "defensibility": 6.6,
        "pain_base": 8.3,
        "one_liner": "面向一个垂直行业提供 AI 电话确认、改期、状态同步和异常转人工。",
        "target_user": "牙科/美容/维修/教育咨询/物流调度等依赖电话确认的 SMB。",
        "pain_scenario": "人工反复拨打确认电话，漏打导致 no-show 或订单延误，且状态无法实时回写。",
        "why_now": "语音模型、实时转写和电话 API 成熟；hackathon 项目中已经出现语音确认 + dashboard + CSV 上传的组合。",
        "mvp_7d": "做 CSV 导入 + 单轮确认外呼 + 结果写回表格。",
        "mvp_14d": "加入多轮对话、短信补充、异常转人工、通话摘要。",
        "mvp_30d": "接入日历/CRM，按行业模板沉淀话术和合规提示。",
        "tech_stack": "Twilio/Vapi/Retell + ASR/TTS + LLM function calling + FastAPI + Postgres + Stripe。",
        "business_model": "按通话分钟、成功确认数或门店月费收费。",
        "risks": "电话合规、用户信任、噪声环境、号码信誉；不要先碰高度监管场景。",
        "validation_plan": "拿 3 家本地服务商的真实预约表做 concierge test，比较 no-show 降低与人工时间节省。",
    },
    "llm_eval": {
        "title": "LLM/Agent 评测与 Prompt 回归测试台",
        "keywords": [
            "llm", "eval", "evals", "evaluation", "benchmark", "prompt",
            "prompts", "test", "testing", "qa", "model", "models", "agent",
            "agents", "guardrail", "redteam", "red-team", "quality",
        ],
        "opc_fit": 9.0,
        "speed_to_mvp": 8.5,
        "defensibility": 7.4,
        "pain_base": 8.0,
        "one_liner": "给正在上线 LLM/Agent 的小团队提供测试集管理、模型对比、回归监控和失败案例分析。",
        "target_user": "AI SaaS、小型研发团队、客服/销售/文档问答产品团队。",
        "pain_scenario": "每次换模型或改 prompt 都担心质量退化，人工抽测慢且不可复现。",
        "why_now": "模型迭代快，agent 工具调用链更复杂；hackathon 项目和 YC 信号都在强调 agent 工作流的可靠性问题。",
        "mvp_7d": "上传测试样例 + 调多个模型 + 输出 pass/fail 表格。",
        "mvp_14d": "加入自动评分器、历史版本对比、CI webhook。",
        "mvp_30d": "支持工具调用 trace、人工标注、团队权限和月度质量报告。",
        "tech_stack": "Next.js + FastAPI + LiteLLM/OpenRouter + Postgres + vector store + GitHub Actions integration。",
        "business_model": "免费层 + 按测试次数/项目数收费；可加企业私有部署。",
        "risks": "已有开源/平台竞品；需要以更简单的 onboarding 或垂直场景取胜。",
        "validation_plan": "找 20 个正在做 AI 功能的开发者，帮他们把 30 个测试样例接入 CI，观察留存与付费意愿。",
    },
    "browser_data": {
        "title": "浏览器自动化与网页数据采集 Agent",
        "keywords": [
            "browser", "web", "scrape", "scraping", "crawler", "crawl", "data",
            "extract", "extraction", "monitor", "tracking", "competitor", "price",
            "inventory", "website", "online", "internet",
        ],
        "opc_fit": 8.2,
        "speed_to_mvp": 7.8,
        "defensibility": 6.8,
        "pain_base": 7.7,
        "one_liner": "把人工浏览网页、复制数据、监控变化的流程做成可配置 agent。",
        "target_user": "电商运营、市场研究、招聘/房产/本地服务信息聚合、小型数据团队。",
        "pain_scenario": "目标网站结构变化频繁，传统爬虫维护成本高，人工采集又慢。",
        "why_now": "视觉/浏览器 agent 能处理更动态的网页，但真正可卖的是垂直数据任务和可靠交付。",
        "mvp_7d": "选择一个垂直数据源，完成登录后数据抽取 + CSV 导出。",
        "mvp_14d": "加入定时监控、字段校验、失败截图和重跑。",
        "mvp_30d": "做成模板市场或 managed data feed。",
        "tech_stack": "Playwright + browser-use/agent framework + proxy/anti-bot 合规策略 + Postgres + alerting。",
        "business_model": "按数据源、监控频率或托管任务收费。",
        "risks": "目标站 ToS、反爬、数据版权；优先做客户有权访问的数据和内部流程自动化。",
        "validation_plan": "让 5 个运营用户列出每周手动采集表，先用脚本替代并按节省时间收费。",
    },
    "devtools": {
        "title": "开发者效率工具：代码/Issue/文档上下文助手",
        "keywords": [
            "developer", "devtool", "devtools", "code", "coding", "github", "issue",
            "issues", "pull", "request", "repo", "repository", "api", "sdk",
            "docs", "documentation", "debug", "review", "ci", "cli",
        ],
        "opc_fit": 8.6,
        "speed_to_mvp": 8.0,
        "defensibility": 6.5,
        "pain_base": 7.5,
        "one_liner": "面向开发者的小工具，自动理解 repo、issue、文档并生成可执行建议或 PR。",
        "target_user": "独立开发者、小型开源项目维护者、技术团队 TL。",
        "pain_scenario": "开发者在 issue、文档、日志和代码之间频繁切换，很多上下文整理工作低价值但耗时。",
        "why_now": "AI coding agent 普及后，开发者愿意为能嵌入 CLI/GitHub 的上下文工具付费。",
        "mvp_7d": "做一个 CLI：输入 repo + issue URL，输出修复计划和相关文件。",
        "mvp_14d": "支持 PR review、文档问答、变更摘要。",
        "mvp_30d": "接 GitHub App，提供团队仪表盘和自动标签/分派。",
        "tech_stack": "Python/Node CLI + GitHub API + tree-sitter + embeddings + LLM + GitHub App。",
        "business_model": "开发者订阅、团队席位、开源免费/私有仓库收费。",
        "risks": "大厂 coding assistant 覆盖面广；需要专注一个高频窄任务。",
        "validation_plan": "在 3 个开源项目上 dogfood，量化节省的 triage/review 时间，并做 Show HN/社区发布。",
    },
    "accessibility_edu": {
        "title": "可访问性/学习辅助 Chrome 插件",
        "keywords": [
            "accessibility", "accessible", "adhd", "dyslexia", "reading", "read",
            "learn", "learning", "education", "student", "students", "content",
            "chrome", "extension", "browser", "assistive",
        ],
        "opc_fit": 8.0,
        "speed_to_mvp": 8.2,
        "defensibility": 5.8,
        "pain_base": 7.6,
        "one_liner": "把难读网页实时改写、分块、朗读或练习化，帮助 ADHD/阅读障碍/非母语用户。",
        "target_user": "学生、知识工作者、阅读障碍用户、家长/老师。",
        "pain_scenario": "长网页和专业内容难以持续阅读，用户需要即时降噪、摘要和互动式理解。",
        "why_now": "浏览器端 LLM 能力和网页改写体验成熟，Devpost hackathon 已出现面向 ADHD/阅读障碍的内容适配项目。",
        "mvp_7d": "Chrome 插件：选中文本后生成易读版 + 关键点。",
        "mvp_14d": "加入分级阅读、朗读、测验卡片和用户偏好。",
        "mvp_30d": "做家长/教师模式，输出学习报告和可分享材料。",
        "tech_stack": "Chrome Extension + local/remote LLM + Readability parser + TTS + Supabase。",
        "business_model": "个人订阅、学校/老师小团队许可、无障碍工具包。",
        "risks": "消费者付费弱；需找到强场景，如考试备考、企业培训或无障碍合规。",
        "validation_plan": "招募 20 名目标用户试读同一材料，比较完成率、理解分数和持续使用意愿。",
    },
    "commerce": {
        "title": "电商售前导购/试穿/商品内容自动化",
        "keywords": [
            "commerce", "ecommerce", "shop", "shopping", "retail", "fashion",
            "try", "virtual", "fitting", "store", "product", "products", "catalog",
            "sales", "customer", "customers", "crm", "sku", "price",
        ],
        "opc_fit": 7.7,
        "speed_to_mvp": 7.2,
        "defensibility": 6.2,
        "pain_base": 7.4,
        "one_liner": "帮助小电商把商品图、尺码、问答、导购和个性化推荐自动化。",
        "target_user": "Shopify/独立站卖家、小品牌、直播/社媒电商运营。",
        "pain_scenario": "商品内容维护、售前问答、尺码推荐和退货原因分析都靠人工，低客单时成本不可控。",
        "why_now": "多模态模型让虚拟试穿、图文生成和个性化导购的 MVP 成本下降。",
        "mvp_7d": "接一个 Shopify 店铺，自动生成商品 FAQ 和售前聊天组件。",
        "mvp_14d": "加入尺码/风格问答、退货原因收集、客服转人工。",
        "mvp_30d": "支持商品图改造、A/B 文案和转化率报告。",
        "tech_stack": "Shopify app + Next.js + image model API + vector search + analytics。",
        "business_model": "按店铺月费 + 用量计费；可加 GMV 阶梯。",
        "risks": "同质化强；必须绑定明确指标，如退货率下降或转化率提升。",
        "validation_plan": "找 5 个小店接入 FAQ/导购，跑 2 周，看客服工单减少和转化变化。",
    },
    "knowledge": {
        "title": "团队知识库 → 可执行 SOP/Skill 的公司大脑",
        "keywords": [
            "knowledge", "docs", "document", "documents", "company", "brain",
            "sop", "skill", "skills", "wiki", "notion", "slack", "drive", "rag",
            "search", "answer", "answers", "assistant", "memory", "context",
        ],
        "opc_fit": 8.3,
        "speed_to_mvp": 7.5,
        "defensibility": 7.6,
        "pain_base": 7.8,
        "one_liner": "把公司文档、Slack、Drive、SOP 转成 agent 可调用的结构化 skill 和问答系统。",
        "target_user": "10-200 人团队、外包/咨询公司、快速增长的创业公司。",
        "pain_scenario": "知识散落在文档、聊天和人脑中，新人 onboarding 慢，AI agent 缺少可靠上下文。",
        "why_now": "YC RFS 明确提到让公司对 AI 可读、把知识转成 skills file 的需求。",
        "mvp_7d": "接 Notion/Google Drive，抽取 SOP 并生成 Markdown skill。",
        "mvp_14d": "加入变更检测、来源引用、审核流程。",
        "mvp_30d": "提供 agent API、权限控制和团队知识健康报告。",
        "tech_stack": "Connectors + embeddings/RAG + structured extraction + MCP/CLI skill export + admin UI。",
        "business_model": "按连接器/用户数收费，初期可做 paid implementation。",
        "risks": "权限与安全要求高；RAG 产品拥挤，需突出“可执行 SOP/skill”而非普通问答。",
        "validation_plan": "为 3 家小团队把 20 条 SOP 转成可执行模板，追踪新人完成任务时间。",
    },
    "creative_media": {
        "title": "AI 图像/视频内容生产小工具",
        "keywords": [
            "image", "images", "video", "videos", "design", "designer", "avatar",
            "edit", "editing", "generate", "generation", "photo", "photos", "media",
            "creative", "content", "thumbnail", "shorts",
        ],
        "opc_fit": 7.3,
        "speed_to_mvp": 8.0,
        "defensibility": 4.9,
        "pain_base": 6.8,
        "one_liner": "针对一个内容生产场景提供极简 AI 生成/编辑流程，例如封面、短视频素材、商品图。",
        "target_user": "创作者、营销人员、电商运营、小工作室。",
        "pain_scenario": "通用生成工具步骤多、风格不一致、难以批量化。",
        "why_now": "多模态模型迭代快，hackathon 和产品发布中大量出现创意媒体 demo。",
        "mvp_7d": "选一个场景做模板化生成，例如 YouTube thumbnail 或商品主图。",
        "mvp_14d": "加入品牌风格、批量处理、导出尺寸。",
        "mvp_30d": "接入工作流：素材库、A/B、团队审批。",
        "tech_stack": "Next.js + image/video model APIs + queue + object storage + template editor。",
        "business_model": "订阅 + 用量点数；可卖模板包。",
        "risks": "API 商品化、同质化、版权；要靠垂直工作流和分发渠道取胜。",
        "validation_plan": "在一个创作者社区发布模板，测 7 日重复使用和付费导出率。",
    },
    "ops_finance": {
        "title": "小企业后台自动化：发票、库存、客户记录",
        "keywords": [
            "invoice", "invoicer", "billing", "payments", "payment", "customer",
            "customers", "crm", "inventory", "warehouse", "records", "admin",
            "bookkeeping", "accounting", "tax", "receipt", "receipts",
        ],
        "opc_fit": 8.1,
        "speed_to_mvp": 7.4,
        "defensibility": 7.0,
        "pain_base": 7.9,
        "one_liner": "把小企业的收款、开票、库存、客户记录做成轻量自动化后台。",
        "target_user": "自由职业者、小批发/零售、线下服务商、微型 B2B。",
        "pain_scenario": "Excel/纸质记录/聊天记录混杂，收款和库存对不上，老板没有实时经营视图。",
        "why_now": "AI 可以从聊天、邮件、票据中抽取结构化数据，降低传统 ERP 的复杂度。",
        "mvp_7d": "发票/收款记录 + 客户列表 + CSV 导入。",
        "mvp_14d": "票据 OCR、库存提醒、WhatsApp/邮件记录抽取。",
        "mvp_30d": "经营看板、自动催收、会计导出。",
        "tech_stack": "FastAPI + Postgres + OCR + Stripe/PayPal/本地支付集成 + lightweight dashboard。",
        "business_model": "月费 + 每笔记录/自动化任务用量；本地化行业模板。",
        "risks": "财税合规因地区不同而复杂；先做记录和提醒，不直接做报税建议。",
        "validation_plan": "找 5 个小老板把当前 Excel 流程搬进 MVP，看每周是否持续录入和愿付费。",
    },
    "health_regulated": {
        "title": "个性化健康/医疗智能化（需谨慎选择非诊断切口）",
        "keywords": [
            "health", "healthcare", "medical", "clinical", "patient", "patients",
            "ehr", "diagnostic", "diagnostics", "genome", "care", "therapy",
            "medicine", "hospital", "doctor", "nurse",
        ],
        "opc_fit": 4.8,
        "speed_to_mvp": 4.0,
        "defensibility": 8.0,
        "pain_base": 8.2,
        "one_liner": "避开诊断治疗，优先做医疗后台行政、患者材料整理或合规文档助手。",
        "target_user": "小诊所、健康教练、医疗后台人员。",
        "pain_scenario": "文档、保险、预约和患者沟通工作量大，但诊疗责任高。",
        "why_now": "个性化健康数据和智能 agent 热度高，但监管和安全要求也高。",
        "mvp_7d": "做非诊断用途的预约/文档整理 demo。",
        "mvp_14d": "加入人工审核、免责声明、审计日志。",
        "mvp_30d": "只在低风险行政流程中试点。",
        "tech_stack": "HIPAA-aware hosting（如适用）+ audit logs + human-in-the-loop + LLM。",
        "business_model": "按门店或后台用户收费。",
        "risks": "监管、责任、数据隐私；不适合作为第一个业余 OPC 项目，除非你有行业资源。",
        "validation_plan": "只验证行政流程痛点，不输出医疗建议。",
    },
    "hardware": {
        "title": "硬件/机器人/芯片/空间基础设施（不适合作为轻量 OPC 首选）",
        "keywords": [
            "hardware", "robot", "robotics", "chip", "chips", "silicon", "space",
            "drone", "drones", "manufacturing", "supply", "chain", "factory",
            "electronics", "inference", "sensor", "sensors",
        ],
        "opc_fit": 3.2,
        "speed_to_mvp": 3.0,
        "defensibility": 8.5,
        "pain_base": 7.8,
        "one_liner": "高潜力但资本/供应链/交付复杂度高，更适合团队公司而非业余 OPC。",
        "target_user": "硬件团队、工业客户、供应链企业。",
        "pain_scenario": "迭代慢、成本高、供应链碎片化。",
        "why_now": "YC 等信号关注硬件供应链、空间计算和 agent inference，但不是 solo side project 友好。",
        "mvp_7d": "如果坚持做，只做软件层：供应商搜索、报价比较、BOM 协作。",
        "mvp_14d": "验证是否能减少硬件团队的采购/设计迭代时间。",
        "mvp_30d": "形成垂直 SaaS 原型，不碰实物制造。",
        "tech_stack": "BOM database + supplier scraping/API + collaboration UI + workflow automation。",
        "business_model": "B2B SaaS 或服务费。",
        "risks": "销售周期长、行业知识门槛高、不可控依赖多。",
        "validation_plan": "先做软件痛点访谈，避免采购库存或制造投入。",
    },
    "other": {
        "title": "其他新奇工具：等待更多证据再投入",
        "keywords": [],
        "opc_fit": 6.5,
        "speed_to_mvp": 6.5,
        "defensibility": 4.5,
        "pain_base": 5.5,
        "one_liner": "有创意信号，但还需要更多痛点和付费证据。",
        "target_user": "暂未明确。",
        "pain_scenario": "需要进一步从用户访谈中提炼。",
        "why_now": "来自近期公开项目或讨论，但多源共振不足。",
        "mvp_7d": "做 landing page + demo 视频。",
        "mvp_14d": "跑 10 次用户访谈。",
        "mvp_30d": "根据访谈结果决定是否编码。",
        "tech_stack": "按具体项目确定。",
        "business_model": "先验证愿付费，再定价。",
        "risks": "可能只是 demo，不是业务。",
        "validation_plan": "先测需求强度，不急于开发。",
    },
}


@dataclass
class Signal:
    source: str
    title: str
    summary: str
    url: str
    created_at: str = ""
    tags: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def metric_summary(self) -> str:
        parts: List[str] = []
        keys = [
            ("votes", "votes"),
            ("comments", "comments"),
            ("stars", "stars"),
            ("forks", "forks"),
            ("points", "points"),
            ("likes", "likes"),
            ("articles", "articles"),
            ("winner", "winner"),
        ]
        for key, label in keys:
            val = self.metrics.get(key)
            if val is None or val == "":
                continue
            if isinstance(val, bool):
                if val:
                    parts.append(label)
            else:
                try:
                    if float(val) > 0:
                        parts.append(f"{label}={int(float(val))}")
                except (TypeError, ValueError):
                    parts.append(f"{label}={val}")
        if self.created_at:
            parts.append(self.created_at[:10])
        return ", ".join(parts) if parts else "n/a"


@dataclass
class ScoreBreakdown:
    heat: float
    pain: float
    opc_fit: float
    speed_to_mvp: float
    defensibility: float
    novelty: float


@dataclass
class Opportunity:
    category: str
    title: str
    signals: List[Signal]
    scores: ScoreBreakdown
    total_score: float
    one_liner: str
    target_user: str
    pain_scenario: str
    why_now: str
    mvp_7d: str
    mvp_14d: str
    mvp_30d: str
    tech_stack: str
    business_model: str
    risks: str
    validation_plan: str

    @property
    def source_mix(self) -> str:
        counts = Counter(s.source for s in self.signals)
        return ", ".join(f"{k}:{v}" for k, v in counts.most_common())

    @property
    def evidence(self) -> List[Signal]:
        return sorted(self.signals, key=signal_heat, reverse=True)


class CollectorError(RuntimeError):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def clean_text(text: str, max_len: int = 500) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def parse_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except Exception:
            return ""
    if isinstance(value, str):
        # Keep ISO-like values as-is; downstream only needs prefix for display.
        return value
    return ""


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def load_config(path: Optional[str]) -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG
    if path:
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = deep_merge(DEFAULT_CONFIG, user_cfg)
    return cfg


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(float(v) for v in weights.values()) or 1.0
    return {k: float(v) / total for k, v in weights.items()}


def request_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    method: str = "GET",
    json_body: Optional[Dict[str, Any]] = None,
    retries: int = 2,
    timeout: int = 25,
) -> Any:
    merged_headers = {"User-Agent": USER_AGENT}
    if headers:
        merged_headers.update(headers)
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            if method.upper() == "POST":
                resp = requests.post(
                    url, params=params, headers=merged_headers, json=json_body, timeout=timeout
                )
            else:
                resp = requests.get(url, params=params, headers=merged_headers, timeout=timeout)
            if resp.status_code >= 400:
                raise CollectorError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - collector should keep going
            last_error = exc
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
    raise CollectorError(str(last_error))


def request_text(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    retries: int = 2,
    timeout: int = 25,
) -> str:
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout
            )
            if resp.status_code >= 400:
                raise CollectorError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
    raise CollectorError(str(last_error))


def collect_hackernews(cfg: Dict[str, Any], since: datetime, verbose: bool = False) -> List[Signal]:
    max_per_source = int(cfg["max_per_source"])
    topics = list(dict.fromkeys(["Show HN"] + cfg.get("seed_topics", [])))
    since_ts = int(since.timestamp())
    per_topic = max(5, math.ceil(max_per_source / max(1, min(len(topics), 8))))
    signals: List[Signal] = []
    for topic in topics[:12]:
        params = {
            "query": topic,
            "tags": "story",
            "numericFilters": f"created_at_i>{since_ts}",
            "hitsPerPage": per_topic,
        }
        data = request_json("https://hn.algolia.com/api/v1/search", params=params)
        for hit in data.get("hits", []):
            title = hit.get("title") or hit.get("story_title") or ""
            if not title:
                continue
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            points = hit.get("points") or 0
            comments = hit.get("num_comments") or 0
            signals.append(
                Signal(
                    source="hackernews",
                    title=clean_text(title, 180),
                    summary=clean_text(hit.get("story_text") or hit.get("comment_text") or title),
                    url=url,
                    created_at=parse_date(hit.get("created_at")),
                    tags=[topic],
                    metrics={"points": points, "comments": comments},
                    raw=hit,
                )
            )
    if verbose:
        print(f"[hackernews] collected {len(signals)}", file=sys.stderr)
    return signals[:max_per_source]


def collect_github(cfg: Dict[str, Any], since: datetime, verbose: bool = False) -> List[Signal]:
    max_per_source = int(cfg["max_per_source"])
    topics = cfg.get("seed_topics", [])
    per_topic = max(5, math.ceil(max_per_source / max(1, min(len(topics), 10))))
    signals: List[Signal] = []
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    since_date = since.date().isoformat()
    for topic in topics[:12]:
        q = f'{topic} created:>={since_date} stars:>=5'
        params = {"q": q, "sort": "stars", "order": "desc", "per_page": per_topic}
        data = request_json(
            "https://api.github.com/search/repositories", params=params, headers=headers
        )
        for item in data.get("items", []):
            title = item.get("full_name") or item.get("name") or ""
            if not title:
                continue
            desc = item.get("description") or ""
            signals.append(
                Signal(
                    source="github",
                    title=clean_text(title, 180),
                    summary=clean_text(desc or title),
                    url=item.get("html_url") or "",
                    created_at=parse_date(item.get("created_at")),
                    tags=(item.get("topics") or []) + [topic],
                    metrics={
                        "stars": item.get("stargazers_count") or 0,
                        "forks": item.get("forks_count") or 0,
                    },
                    raw={
                        "language": item.get("language"),
                        "updated_at": item.get("updated_at"),
                        "license": item.get("license"),
                    },
                )
            )
    if verbose:
        print(f"[github] collected {len(signals)}", file=sys.stderr)
    return signals[:max_per_source]


def collect_producthunt(cfg: Dict[str, Any], since: datetime, verbose: bool = False) -> List[Signal]:
    token = os.getenv("PRODUCTHUNT_TOKEN") or os.getenv("PH_TOKEN")
    if not token:
        raise CollectorError("PRODUCTHUNT_TOKEN/PH_TOKEN not set")
    max_per_source = int(cfg["max_per_source"])
    query = """
    query($first: Int!, $postedAfter: DateTime!) {
      posts(first: $first, order: VOTES, featured: true, postedAfter: $postedAfter) {
        edges {
          node {
            id
            name
            tagline
            description
            votesCount
            commentsCount
            createdAt
            url
            website
            topics(first: 8) { edges { node { name } } }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}
    body = {"query": query, "variables": {"first": max_per_source, "postedAfter": since.isoformat()}}
    data = request_json(
        "https://api.producthunt.com/v2/api/graphql",
        method="POST",
        json_body=body,
        headers=headers,
    )
    if data.get("errors"):
        raise CollectorError(f"Product Hunt GraphQL error: {data['errors'][:1]}")
    signals: List[Signal] = []
    for edge in (data.get("data", {}).get("posts", {}).get("edges", []) or []):
        node = edge.get("node") or {}
        topics = [
            t.get("node", {}).get("name", "")
            for t in (node.get("topics", {}).get("edges", []) or [])
            if t.get("node")
        ]
        title = node.get("name") or ""
        if not title:
            continue
        signals.append(
            Signal(
                source="producthunt",
                title=clean_text(title, 180),
                summary=clean_text(node.get("tagline") or node.get("description") or title),
                url=node.get("url") or node.get("website") or "",
                created_at=parse_date(node.get("createdAt")),
                tags=topics,
                metrics={
                    "votes": node.get("votesCount") or 0,
                    "comments": node.get("commentsCount") or 0,
                },
                raw={"website": node.get("website"), "id": node.get("id")},
            )
        )
    if verbose:
        print(f"[producthunt] collected {len(signals)}", file=sys.stderr)
    return signals


def collect_devpost(cfg: Dict[str, Any], since: datetime, verbose: bool = False) -> List[Signal]:
    max_per_source = int(cfg["max_per_source"])
    urls: List[str] = []
    for topic in cfg.get("seed_topics", [])[:8]:
        urls.append(f"https://devpost.com/software/search?query={quote_plus(topic)}")
    urls.extend(cfg.get("devpost_galleries", []) or [])

    signals: List[Signal] = []
    seen_urls: set[str] = set()
    for page_url in urls:
        html = request_text(page_url)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/software/" not in href:
                continue
            full_url = urljoin("https://devpost.com", href.split("?")[0])
            if full_url in seen_urls or full_url.rstrip("/").endswith("/software"):
                continue
            title = clean_text(a.get_text(" ", strip=True), 180)
            if len(title) < 4:
                continue
            parent = a.find_parent(["article", "li", "div", "section"])
            parent_text = clean_text(parent.get_text(" ", strip=True) if parent else title, 500)
            if len(parent_text) < len(title):
                parent_text = title
            winner = "winner" in parent_text.lower()
            nums = [int(n) for n in re.findall(r"\b(\d{1,5})\b", parent_text)]
            metrics: Dict[str, Any] = {"winner": winner}
            if nums:
                # Devpost cards often end with like/comment counts. This is heuristic only.
                metrics["likes"] = max(nums[-2:]) if len(nums) >= 2 else nums[-1]
            signals.append(
                Signal(
                    source="devpost",
                    title=title,
                    summary=parent_text,
                    url=full_url,
                    tags=["hackathon", "devpost"] + (["winner"] if winner else []),
                    metrics=metrics,
                    raw={"page_url": page_url},
                )
            )
            seen_urls.add(full_url)
            if len(signals) >= max_per_source:
                break
        if len(signals) >= max_per_source:
            break
    if verbose:
        print(f"[devpost] collected {len(signals)}", file=sys.stderr)
    return signals


def collect_yc_rfs(cfg: Dict[str, Any], since: datetime, verbose: bool = False) -> List[Signal]:
    max_per_source = min(int(cfg["max_per_source"]), 20)
    html = request_text("https://www.ycombinator.com/rfs")
    soup = BeautifulSoup(html, "html.parser")
    signals: List[Signal] = []
    for h in soup.find_all(["h2", "h3"]):
        title = clean_text(h.get_text(" ", strip=True).replace("#", ""), 160)
        if not title or title.lower() in {"requests for startups", "company"}:
            continue
        parts: List[str] = []
        for sib in h.find_next_siblings():
            if getattr(sib, "name", None) in {"h2", "h3"}:
                break
            txt = clean_text(sib.get_text(" ", strip=True), 240)
            if txt:
                parts.append(txt)
            if len(" ".join(parts)) > 450:
                break
        summary = clean_text(" ".join(parts), 500)
        if len(summary) < 20:
            continue
        anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        signals.append(
            Signal(
                source="yc_rfs",
                title=title,
                summary=summary,
                url=f"https://www.ycombinator.com/rfs#{anchor}",
                tags=["request-for-startups", "yc"],
                metrics={"votes": 0},
                raw={},
            )
        )
        if len(signals) >= max_per_source:
            break
    if verbose:
        print(f"[yc_rfs] collected {len(signals)}", file=sys.stderr)
    return signals


def _hf_repo_from_trending_item(item: Any) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    for key in ("repoData", "repo", "model", "space", "dataset"):
        if isinstance(item.get(key), dict):
            return item[key]
    return item


def collect_huggingface(cfg: Dict[str, Any], since: datetime, verbose: bool = False) -> List[Signal]:
    max_per_source = int(cfg["max_per_source"])
    signals: List[Signal] = []
    for hf_type in ("space", "model"):
        try:
            data = request_json("https://huggingface.co/api/trending", params={"type": hf_type})
        except Exception as exc:  # noqa: BLE001 - best effort source
            if verbose:
                print(f"[huggingface:{hf_type}] skipped: {exc}", file=sys.stderr)
            continue
        if not isinstance(data, list):
            continue
        for item in data[: max(5, max_per_source // 2)]:
            repo = _hf_repo_from_trending_item(item)
            repo_id = repo.get("id") or repo.get("name") or repo.get("repo_id") or repo.get("repoId")
            if not repo_id:
                continue
            desc = repo.get("description") or item.get("description") or repo_id
            likes = repo.get("likes") or item.get("likes") or 0
            signals.append(
                Signal(
                    source="huggingface",
                    title=clean_text(str(repo_id), 180),
                    summary=clean_text(str(desc), 400),
                    url=f"https://huggingface.co/{'spaces/' if hf_type == 'space' else ''}{repo_id}",
                    created_at=parse_date(repo.get("createdAt") or item.get("createdAt")),
                    tags=["huggingface", hf_type],
                    metrics={"likes": likes},
                    raw={"type": hf_type},
                )
            )
            if len(signals) >= max_per_source:
                break
        if len(signals) >= max_per_source:
            break
    if verbose:
        print(f"[huggingface] collected {len(signals)}", file=sys.stderr)
    return signals


def collect_gdelt(cfg: Dict[str, Any], since: datetime, verbose: bool = False) -> List[Signal]:
    max_per_source = min(int(cfg["max_per_source"]), 12)
    days = int(cfg.get("lookback_days", 30))
    signals: List[Signal] = []
    for topic in cfg.get("seed_topics", [])[:max_per_source]:
        params = {
            "query": topic,
            "mode": "timelinevol",
            "format": "json",
            "timespan": f"{days}d",
        }
        try:
            data = request_json("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
        except Exception as exc:  # noqa: BLE001
            if verbose:
                print(f"[gdelt:{topic}] skipped: {exc}", file=sys.stderr)
            continue
        timeline = data.get("timeline") or data.get("data") or []
        article_score = 0.0
        if isinstance(timeline, list):
            for row in timeline:
                if not isinstance(row, dict):
                    continue
                for key in ("value", "count", "norm", "Volume Intensity"):
                    if key in row:
                        try:
                            article_score += float(row[key])
                        except Exception:
                            pass
        signals.append(
            Signal(
                source="gdelt",
                title=f"News heat: {topic}",
                summary=f"GDELT timeline volume signal for '{topic}' over {days} days.",
                url="https://www.gdeltproject.org/",
                tags=[topic, "news-heat"],
                metrics={"articles": round(article_score, 2)},
                raw={"topic": topic},
            )
        )
    if verbose:
        print(f"[gdelt] collected {len(signals)}", file=sys.stderr)
    return signals


def sample_signals() -> List[Signal]:
    """Representative signals for smoke testing without network access."""
    return [
        Signal(
            source="devpost",
            title="CallVance",
            summary="Automates AI-powered voice calls to confirm appointments, update statuses in real time, and reduce no-shows.",
            url="https://devpost.com/software/callvance",
            tags=["hackathon", "winner", "voice agent"],
            metrics={"winner": True, "likes": 12},
        ),
        Signal(
            source="devpost",
            title="ModelMash: Find the Perfect LLM",
            summary="Test hundreds of LLMs for a specific task with prompts and success criteria.",
            url="https://devpost.com/software/modelmash-find-the-perfect-llm",
            tags=["hackathon", "winner", "llm eval"],
            metrics={"winner": True, "likes": 12},
        ),
        Signal(
            source="devpost",
            title="Mochi - Making hard content enjoyable",
            summary="Chrome extension that adapts web content for users with reading disabilities, ADHD, and dyslexia.",
            url="https://devpost.com/software/mochi-making-hard-content-enjoyable",
            tags=["hackathon", "accessibility", "chrome extension"],
            metrics={"winner": True, "likes": 104},
        ),
        Signal(
            source="devpost",
            title="LookMate – Your virtual fashion companion",
            summary="Try Before You Buy: realistic virtual fitting rooms for online shopping.",
            url="https://devpost.com/software/lookmate",
            tags=["hackathon", "ecommerce ai"],
            metrics={"winner": True, "likes": 7},
        ),
        Signal(
            source="yc_rfs",
            title="AI-native companies that sell the service",
            summary="YC is interested in AI-native companies replacing outsourced services such as accounting, tax, audit, compliance and healthcare administration.",
            url="https://www.ycombinator.com/rfs#ai-native-companies-that-sell-the-service",
            tags=["yc", "ai agent", "service"],
            metrics={},
        ),
        Signal(
            source="yc_rfs",
            title="Company brain and skills file",
            summary="Turn company context into skills files so AI systems can do work safely and consistently.",
            url="https://www.ycombinator.com/rfs#company-brain-and-skills-file",
            tags=["yc", "knowledge", "skill"],
            metrics={},
        ),
        Signal(
            source="hackernews",
            title="Show HN: Browser agent that fills forms and extracts structured data",
            summary="A developer tool for automating repetitive browser tasks with human review.",
            url="https://news.ycombinator.com/item?id=sample-browser-agent",
            tags=["Show HN", "browser automation"],
            metrics={"points": 123, "comments": 41},
        ),
        Signal(
            source="github",
            title="example/agent-evals",
            summary="Open-source prompt and tool-call evaluation framework for AI agents.",
            url="https://github.com/example/agent-evals",
            tags=["llm", "eval", "agent"],
            metrics={"stars": 850, "forks": 73},
        ),
        Signal(
            source="producthunt",
            title="OpsPilot for SMBs",
            summary="AI agent that handles repetitive back-office workflows for small businesses.",
            url="https://www.producthunt.com/products/opspilot-for-smbs",
            tags=["ai", "automation", "smb"],
            metrics={"votes": 230, "comments": 34},
        ),
    ]


def collect_all(cfg: Dict[str, Any], sample: bool = False, verbose: bool = False) -> Tuple[List[Signal], List[str]]:
    if sample:
        return sample_signals(), []

    since = now_utc() - timedelta(days=int(cfg.get("lookback_days", 30)))
    source_flags = cfg.get("sources", {})
    collectors = [
        ("hackernews", collect_hackernews),
        ("github", collect_github),
        ("producthunt", collect_producthunt),
        ("devpost", collect_devpost),
        ("yc_rfs", collect_yc_rfs),
        ("huggingface", collect_huggingface),
        ("gdelt", collect_gdelt),
    ]
    signals: List[Signal] = []
    skipped: List[str] = []
    for name, func in collectors:
        if not source_flags.get(name, False):
            continue
        try:
            part = func(cfg, since, verbose=verbose)
            signals.extend(part)
        except Exception as exc:  # noqa: BLE001 - preserve pipeline
            skipped.append(f"{name}: {exc}")
            if verbose:
                print(f"[{name}] skipped: {exc}", file=sys.stderr)
    return dedupe_signals(signals), skipped


def signal_key(signal: Signal) -> str:
    if signal.url:
        u = signal.url.lower().rstrip("/")
        if u and u not in {"https://github.com", "https://news.ycombinator.com"}:
            return u
    return re.sub(r"[^a-z0-9]+", "", signal.title.lower())[:80]


def dedupe_signals(signals: Sequence[Signal]) -> List[Signal]:
    seen: Dict[str, Signal] = {}
    for sig in signals:
        key = signal_key(sig)
        if not key:
            continue
        if key not in seen or signal_heat(sig) > signal_heat(seen[key]):
            seen[key] = sig
    return list(seen.values())


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS and not t.isdigit()]


def category_for_signal(signal: Signal) -> str:
    text = " ".join([signal.title, signal.summary, " ".join(signal.tags)]).lower()
    best_cat = "other"
    best_score = 0
    for cat, meta in CATEGORY_META.items():
        if cat == "other":
            continue
        score = 0
        for kw in meta.get("keywords", []):
            # Phrase keywords get a stronger boost.
            if " " in kw:
                if kw in text:
                    score += 3
            elif re.search(rf"\b{re.escape(kw)}\b", text):
                score += 1
        if score > best_score:
            best_cat = cat
            best_score = score
    return best_cat


def signal_heat(signal: Signal) -> float:
    metrics = signal.metrics or {}
    metric_score = 0.0
    for key, factor in [
        ("votes", 1.0),
        ("comments", 0.8),
        ("stars", 1.1),
        ("forks", 0.6),
        ("points", 0.9),
        ("likes", 0.7),
        ("articles", 0.5),
    ]:
        try:
            metric_score += factor * math.log1p(float(metrics.get(key) or 0.0))
        except Exception:
            pass
    if metrics.get("winner"):
        metric_score += 1.8
    source_weight = SOURCE_WEIGHTS.get(signal.source, 0.8)
    return min(10.0, source_weight * (2.0 + metric_score / 1.8))


def pain_signal_boost(signals: Sequence[Signal]) -> float:
    if not signals:
        return 0.0
    hits = 0
    total = 0
    for sig in signals:
        toks = set(tokenize(sig.title + " " + sig.summary))
        total += 1
        hits += len(toks & PAIN_TERMS)
    return min(1.5, hits / max(1, total) * 0.25)


def evidence_density_boost(signals: Sequence[Signal]) -> float:
    source_count = len(set(s.source for s in signals))
    count_boost = min(1.2, len(signals) * 0.12)
    source_boost = min(1.4, source_count * 0.35)
    return count_boost + source_boost


def build_opportunities(signals: Sequence[Signal], cfg: Dict[str, Any]) -> List[Opportunity]:
    clusters: Dict[str, List[Signal]] = defaultdict(list)
    for sig in signals:
        clusters[category_for_signal(sig)].append(sig)

    weights = normalize_weights(cfg.get("weights", DEFAULT_CONFIG["weights"]))
    constraints = cfg.get("opc_constraints", {})
    avoid_terms = " ".join(constraints.get("avoid", [])).lower()
    opportunities: List[Opportunity] = []

    for cat, sigs in clusters.items():
        if not sigs:
            continue
        meta = CATEGORY_META.get(cat, CATEGORY_META["other"])
        sigs_sorted = sorted(sigs, key=signal_heat, reverse=True)
        heat = min(10.0, sum(signal_heat(s) for s in sigs_sorted[:8]) / max(1, min(8, len(sigs_sorted))) + evidence_density_boost(sigs_sorted))
        pain = min(10.0, float(meta.get("pain_base", 6.0)) + pain_signal_boost(sigs_sorted))
        opc_fit = float(meta.get("opc_fit", 6.0))
        speed = float(meta.get("speed_to_mvp", 6.0))
        defensibility = float(meta.get("defensibility", 5.0))
        novelty = min(
            10.0,
            4.2
            + 0.7 * len({s.source for s in sigs_sorted})
            + 0.5 * sum(1 for s in sigs_sorted if s.source in {"devpost", "producthunt", "huggingface"})
            + 0.7 * sum(1 for s in sigs_sorted if s.metrics.get("winner")),
        )

        combined_text = " ".join(s.title + " " + s.summary for s in sigs_sorted).lower()
        # Penalize categories that conflict with solo/side-project constraints.
        for avoid in constraints.get("avoid", []) or []:
            if avoid.lower() and avoid.lower() in combined_text:
                opc_fit -= 1.0
                speed -= 0.7
        if "hardware" in combined_text or "manufacturing" in combined_text:
            if "hardware manufacturing" in avoid_terms:
                opc_fit -= 0.8
        if "clinical" in combined_text or "diagnostic" in combined_text:
            if "clinical diagnosis" in avoid_terms:
                opc_fit -= 1.2
                speed -= 0.8

        opc_fit = max(1.0, min(10.0, opc_fit))
        speed = max(1.0, min(10.0, speed))
        scores = ScoreBreakdown(
            heat=round(heat, 2),
            pain=round(pain, 2),
            opc_fit=round(opc_fit, 2),
            speed_to_mvp=round(speed, 2),
            defensibility=round(defensibility, 2),
            novelty=round(novelty, 2),
        )
        total = (
            weights.get("heat", 0) * scores.heat
            + weights.get("pain", 0) * scores.pain
            + weights.get("opc_fit", 0) * scores.opc_fit
            + weights.get("speed_to_mvp", 0) * scores.speed_to_mvp
            + weights.get("defensibility", 0) * scores.defensibility
            + weights.get("novelty", 0) * scores.novelty
        )
        why_now = meta.get("why_now", CATEGORY_META["other"]["why_now"])
        # Add evidence-aware sentence without overfitting to one source.
        source_mix = Counter(s.source for s in sigs_sorted)
        why_now = f"{why_now} 本次抓取中该方向出现 {len(sigs_sorted)} 条信号，来源分布：" + ", ".join(
            f"{k}={v}" for k, v in source_mix.most_common()
        ) + "。"
        opportunities.append(
            Opportunity(
                category=cat,
                title=meta.get("title", cat),
                signals=sigs_sorted,
                scores=scores,
                total_score=round(total, 2),
                one_liner=meta.get("one_liner", ""),
                target_user=meta.get("target_user", ""),
                pain_scenario=meta.get("pain_scenario", ""),
                why_now=why_now,
                mvp_7d=meta.get("mvp_7d", ""),
                mvp_14d=meta.get("mvp_14d", ""),
                mvp_30d=meta.get("mvp_30d", ""),
                tech_stack=meta.get("tech_stack", ""),
                business_model=meta.get("business_model", ""),
                risks=meta.get("risks", ""),
                validation_plan=meta.get("validation_plan", ""),
            )
        )

    opportunities.sort(key=lambda o: o.total_score, reverse=True)
    return opportunities[: int(cfg.get("top_opportunities", 8))]


def default_template_text() -> str:
    template_path = Path(__file__).resolve().parents[1] / "templates" / "report.md.j2"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return """
# OPC 创业产品创意分析报告

生成时间：{{ generated_at }}

{% for opp in opportunities %}
## {{ loop.index }}. {{ opp.title }} — {{ '%.1f'|format(opp.total_score) }}/10

{{ opp.one_liner }}

证据：{% for e in opp.evidence[:3] %}[{{ e.title }}]({{ e.url }}){% if not loop.last %}, {% endif %}{% endfor %}
{% endfor %}
"""


def render_report(signals: Sequence[Signal], opportunities: Sequence[Opportunity], cfg: Dict[str, Any]) -> str:
    template = Template(default_template_text())
    top_signals = sorted(signals, key=signal_heat, reverse=True)[:30]
    return template.render(
        generated_at=now_utc().astimezone().isoformat(timespec="seconds"),
        lookback_days=cfg.get("lookback_days", 30),
        signal_count=len(signals),
        opportunity_count=len(opportunities),
        opportunities=opportunities,
        top_signals=top_signals,
    )


def signal_to_dict(sig: Signal) -> Dict[str, Any]:
    d = asdict(sig)
    d["metric_summary"] = sig.metric_summary
    d["heat_score"] = round(signal_heat(sig), 3)
    d["category"] = category_for_signal(sig)
    return d


def opportunity_to_dict(opp: Opportunity) -> Dict[str, Any]:
    return {
        "category": opp.category,
        "title": opp.title,
        "total_score": opp.total_score,
        "scores": asdict(opp.scores),
        "source_mix": opp.source_mix,
        "one_liner": opp.one_liner,
        "target_user": opp.target_user,
        "pain_scenario": opp.pain_scenario,
        "why_now": opp.why_now,
        "mvp_7d": opp.mvp_7d,
        "mvp_14d": opp.mvp_14d,
        "mvp_30d": opp.mvp_30d,
        "tech_stack": opp.tech_stack,
        "business_model": opp.business_model,
        "risks": opp.risks,
        "validation_plan": opp.validation_plan,
        "evidence": [signal_to_dict(s) for s in opp.evidence[:10]],
    }


def write_outputs(
    report: str,
    signals: Sequence[Signal],
    opportunities: Sequence[Opportunity],
    skipped: Sequence[str],
    cfg: Dict[str, Any],
    out_path: str,
    json_out_path: Optional[str],
) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")

    if json_out_path:
        payload = {
            "generated_at": now_utc().isoformat(),
            "config": cfg,
            "skipped_sources": list(skipped),
            "signals": [signal_to_dict(s) for s in signals],
            "opportunities": [opportunity_to_dict(o) for o in opportunities],
        }
        jout = Path(json_out_path)
        jout.parent.mkdir(parents=True, exist_ok=True)
        jout.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def print_summary(opportunities: Sequence[Opportunity], skipped: Sequence[str], out_path: str, json_out_path: Optional[str]) -> None:
    print(f"Report written: {out_path}")
    if json_out_path:
        print(f"JSON written:   {json_out_path}")
    if skipped:
        print("Skipped sources:")
        for item in skipped:
            print(f"  - {item}")
    print("Top opportunities:")
    for idx, opp in enumerate(opportunities[:5], 1):
        print(f"  {idx}. {opp.title} — {opp.total_score:.1f}/10 ({opp.source_mix})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mine OPC product ideas and generate a report.")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="Collect, score, and render report")
    run.add_argument("--config", default=None, help="YAML config path")
    run.add_argument("--out", default="reports/opc_ideas.md", help="Markdown report output path")
    run.add_argument("--json-out", default=None, help="JSON output path")
    run.add_argument("--days", type=int, default=None, help="Override lookback_days")
    run.add_argument("--max-per-source", type=int, default=None, help="Override max_per_source")
    run.add_argument("--top", type=int, default=None, help="Override top_opportunities")
    run.add_argument("--sample", action="store_true", help="Use built-in sample signals; no network")
    run.add_argument("--verbose", action="store_true", help="Print collector diagnostics")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "run":
        parser.print_help()
        return 2

    cfg = load_config(args.config)
    if args.days is not None:
        cfg["lookback_days"] = args.days
    if args.max_per_source is not None:
        cfg["max_per_source"] = args.max_per_source
    if args.top is not None:
        cfg["top_opportunities"] = args.top

    signals, skipped = collect_all(cfg, sample=args.sample, verbose=args.verbose)
    signals = dedupe_signals(signals)
    opportunities = build_opportunities(signals, cfg)
    report = render_report(signals, opportunities, cfg)
    write_outputs(report, signals, opportunities, skipped, cfg, args.out, args.json_out)
    print_summary(opportunities, skipped, args.out, args.json_out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
