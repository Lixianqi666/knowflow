"""生成模拟数据：用户、知识库、文档、Agent、场景、对话"""
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def h(s):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))

def now(d=0):
    return (datetime.utcnow() + timedelta(days=d)).isoformat()

USERS = [
    ("3423554221@qq.com", "李先齐", "admin", "admin123"),
    ("zhangwei@company.com", "张伟", "member", "pass123"),
    ("lina@company.com", "李娜", "member", "pass123"),
    ("wangfang@company.com", "王芳", "member", "pass123"),
    ("liuyang@company.com", "刘洋", "member", "pass123"),
    ("chenming@company.com", "陈明", "member", "pass123"),
]

KBS = [
    ("公司制度", "公司规章制度、行政管理办法、员工手册等"),
    ("技术文档", "技术架构、开发规范、API文档、部署指南等"),
    ("产品知识", "产品介绍、功能说明、使用教程、FAQ等"),
    ("人事行政", "招聘流程、薪酬福利、培训发展、考勤制度等"),
]

DOCS = [
    # 公司制度
    ("员工手册2024版", "公司制度", "# 员工手册2024版\n\n## 第一章 公司简介\n\n本公司成立于2018年，是一家专注于人工智能和知识管理领域的科技公司。公司总部位于北京，在上海、深圳设有分部。\n\n## 第二章 入职管理\n\n### 2.1 入职流程\n1. 接到offer后，请在规定时间内完成入职材料准备\n2. 入职当天携带身份证、学历证明、离职证明等材料\n3. 由HR引导完成系统账号开通、工位安排等\n\n### 2.2 试用期规定\n- 试用期一般为3个月，特殊岗位可延长至6个月\n- 试用期内享受正式薪资的80%\n- 试用期结束前一周进行转正评估\n\n## 第三章 考勤制度\n\n### 3.1 工作时间\n- 周一至周五 9:00-18:00，午休12:00-13:00\n- 每周工作5天，双休\n\n### 3.2 打卡规定\n- 每日需打卡两次：上班打卡（9:00前）和下班打卡（18:00后）\n- 迟到/早退超过30分钟按旷工半天处理\n- 每月允许3次忘打卡补卡机会\n\n### 3.3 请假制度\n- 事假：需提前1天申请，无薪\n- 病假：需提供医院证明，带薪（每年累计不超过15天）\n- 年假：工作满1年享5天，满5年享10天，满10年享15天\n- 婚假：3天（晚婚加7天）\n- 产假：女员工158天，男员工陪产假15天\n\n## 第四章 薪酬福利\n\n### 4.1 薪资结构\n- 基本工资 + 绩效奖金 + 项目奖金\n- 每月15日发放上月工资\n- 年终奖根据公司业绩和个人绩效发放\n\n### 4.2 社会保险\n- 五险一金：养老保险、医疗保险、失业保险、工伤保险、生育保险、住房公积金\n- 补充商业保险\n\n### 4.3 其他福利\n- 免费三餐 + 下午茶\n- 年度体检\n- 团建活动（每季度一次）\n- 学习基金（每人每年5000元）\n- 弹性工作制（核心工作时间10:00-16:00）"),
    ("信息安全管理制度", "公司制度", "# 信息安全管理制度\n\n## 1. 总则\n\n### 1.1 目的\n为保障公司信息资产安全，防范信息安全风险，特制定本制度。\n\n### 1.2 适用范围\n本制度适用于公司全体员工及外包人员。\n\n## 2. 密码管理\n\n### 2.1 密码策略\n- 密码长度不少于8位\n- 必须包含大小写字母、数字和特殊字符\n- 每90天强制更换密码\n- 不得使用前3次使用过的密码\n\n### 2.2 账号管理\n- 离职当天必须注销所有系统账号\n- 长期不使用（超过30天）的账号自动锁定\n- 特殊权限账号需经部门负责人审批\n\n## 3. 数据分类\n\n### 3.1 数据密级\n- **绝密**：核心商业机密、未公开财务数据\n- **机密**：客户数据、源代码、核心技术文档\n- **内部**：内部通知、会议纪要、工作计划\n- **公开**：官网内容、公开宣传材料\n\n### 3.2 数据使用规范\n- 绝密/机密数据不得在公共网络传输\n- 禁止将公司数据存储在个人网盘\n- 打印机密文件需经审批并登记\n\n## 4. 网络安全\n\n- 禁止私自搭建WiFi热点\n- 禁止使用未经授权的VPN\n- 发现安全事件立即报告IT部门"),
    ("远程办公管理规定", "公司制度", "# 远程办公管理规定\n\n## 1. 适用范围\n\n经部门负责人批准的远程办公申请，适用于以下情况：\n- 因交通/天气等不可抗力无法到岗\n- 需要集中精力完成紧急项目\n- 医生建议居家休养\n\n## 2. 申请流程\n\n1. 提前1个工作日在OA系统提交远程办公申请\n2. 部门负责人审批\n3. 审批通过后通知IT部门开通远程访问权限\n\n## 3. 工作要求\n\n### 3.1 考勤\n- 远程办公期间需在企业微信打卡\n- 核心工作时间（10:00-16:00）必须在线\n- 每日工作结束前在群里汇报当日工作\n\n### 3.2 沟通\n- 保持企业微信/飞书在线状态\n- 重要会议需开启视频\n- 紧急事项电话联系\n\n### 3.3 安全\n- 使用公司VPN连接内网\n- 不得在公共场所处理机密文件\n- 远程办公设备需安装杀毒软件"),
    # 技术文档
    ("API接口文档v2.0", "技术文档", "# API接口文档 v2.0\n\n## 基础信息\n\n- Base URL: https://api.knowflow.com/v2\n- 认证方式: Bearer Token (JWT)\n- 请求格式: JSON\n- 响应格式: JSON\n\n## 认证接口\n\n### POST /auth/login\n用户登录获取token\n\n```json\n请求: {\n  \"email\": \"user@company.com\",\n  \"password\": \"xxx\"\n}\n响应: {\n  \"token\": \"eyJ...\",\n  \"user\": {\"id\": \"...\", \"name\": \"...\"}\n}\n```\n\n### POST /auth/register\n用户注册\n\n```json\n请求: {\n  \"email\": \"new@company.com\",\n  \"password\": \"xxx\",\n  \"name\": \"张三\"\n}\n```\n\n## 对话接口\n\n### POST /chat/conversations\n创建对话\n\n### POST /chat/conversations/{id}/messages\n发送消息（SSE流式响应）\n\n事件类型：\n- `sources`: 检索来源\n- `token`: 逐token生成\n- `structured`: 结构化输出\n- `done`: 生成完成\n- `error`: 错误信息\n\n## 文档接口\n\n### POST /documents/upload\n上传文档（multipart/form-data）\n支持格式：txt, md, pdf, docx, xlsx\n\n### GET /documents\n获取文档列表\n\n### DELETE /documents/{id}\n删除文档"),
    ("系统架构设计文档", "技术文档", "# KnowFlow 系统架构设计\n\n## 1. 系统概述\n\nKnowFlow 是一个企业级知识库 RAG 问答系统，基于检索增强生成（RAG）技术，为企业提供智能文档问答服务。\n\n## 2. 技术栈\n\n| 层级 | 技术 |\n|------|------|\n| 前端 | Next.js 15 + Tailwind CSS + Zustand |\n| 后端 | FastAPI + SQLAlchemy async |\n| 数据库 | PostgreSQL 16 + pgvector |\n| 缓存 | Redis 7 |\n| 任务队列 | Celery + Redis broker |\n| 向量模型 | BAAI/bge-m3 |\n| LLM | DeepSeek-V3 (via SiliconFlow) |\n| 重排模型 | BGE-Reranker |\n\n## 3. 核心流程\n\n```\n用户提问 → 查询改写 → 双路检索(向量+BM25) → RRF融合 → 可选精排 → LLM生成 → 流式输出\n```\n\n### 3.1 检索管道\n1. **查询改写**：使用LLM进行代词消解和关键术语提取\n2. **向量检索**：pgvector cosine相似度搜索\n3. **BM25检索**：PostgreSQL全文检索(tsvector)\n4. **RRF融合**：Reciprocal Rank Fusion排序\n5. **LIKE补充**：子串匹配兜底\n6. **精排**：可选BGE-Reranker重排序\n\n### 3.2 文档处理\n1. 上传 → 文本提取(pdfplumber/docx)\n2. 分块：Markdown标题感知，512 token/64 overlap\n3. 向量化：BGE-M3 embedding\n4. 存储：pgvector + tsvector\n\n## 4. 部署架构\n\n```\nNginx (80/443) → Backend (8000) → PostgreSQL + Redis\n                  ↘ Worker (Celery)\nFrontend (3000) ↗\n```\n\n所有服务通过Docker Compose编排，支持一键部署。"),
    ("数据库设计文档", "技术文档", "# 数据库设计文档\n\n## 核心表\n\n### users\n用户表，存储系统用户信息\n\n### documents\n文档表，存储上传的文档元数据\n- source_id: 关联数据源\n- kb_id: 关联知识库\n- status: pending/processing/indexed/failed\n\n### document_chunks\n文档分块表，存储向量化后的文本块\n- embedding: vector(1024) pgvector向量\n- tsvector_content: 全文检索向量\n\n### conversations\n对话表\n\n### messages\n消息表，存储对话消息\n- role: user/assistant/system\n- sources: JSONB 检索来源\n\n### agents\n智能体表\n\n### knowledge_bases\n知识库表\n\n## 索引策略\n\n- document_chunks: GIN索引 on tsvector_content\n- document_chunks: IVFFlat索引 on embedding (cosine)\n- messages: 复合索引 (conversation_id, created_at)\n- 所有外键字段均有索引"),
    # 产品知识
    ("KnowFlow产品介绍", "产品知识", "# KnowFlow 产品介绍\n\n## 产品定位\n\nKnowFlow 是一款面向企业的智能知识库问答系统，基于 RAG（检索增强生成）技术，帮助企业高效管理和利用内部知识资产。\n\n## 核心功能\n\n### 1. 智能问答\n- 基于企业文档的精准问答\n- 支持多轮对话，理解上下文\n- 流式输出，实时生成回答\n- 引用来源可追溯\n\n### 2. 知识库管理\n- 支持多种文档格式（PDF/Word/Excel/Markdown/TXT）\n- 智能分块和向量化\n- 知识库分类管理\n- 权限控制\n\n### 3. Agent 平台\n- 可创建定制化AI助手\n- 每个Agent可关联独立知识库\n- 支持自定义系统提示词\n\n### 4. 管理后台\n- 用户管理与权限控制\n- 文档管理与监控\n- 使用统计与分析\n- 审计日志\n\n## 技术优势\n\n- **双路召回**：向量检索 + BM25全文检索\n- **智能分块**：Markdown标题感知，保留文档结构\n- **流式响应**：毫秒级首token延迟\n- **权限隔离**：文档级细粒度权限控制\n\n## 适用场景\n\n- 企业内部知识库\n- 客户服务智能助手\n- 技术文档问答\n- HR政策咨询\n- IT帮助台"),
    ("常见问题FAQ", "产品知识", "# KnowFlow 常见问题 FAQ\n\n## Q: 支持哪些文档格式？\nA: 目前支持 PDF、Word (.docx)、Excel (.xlsx)、Markdown (.md) 和纯文本 (.txt)。单个文件大小限制 20MB。\n\n## Q: 文档上传后多久可以查询？\nA: 文档上传后会自动进行文本提取、分块和向量化处理，通常需要 1-5 分钟，取决于文档大小。状态显示为\"已索引\"后即可查询。\n\n## Q: 如何提高问答准确率？\nA: \n1. 确保文档内容质量高、结构清晰\n2. 使用知识库分类管理相关文档\n3. 调整检索参数（top_k、阈值）\n4. 使用Prompt模板定制回答风格\n\n## Q: 数据安全如何保障？\nA:\n- 所有数据存储在私有服务器\n- 文档级权限控制\n- HTTPS加密传输\n- 支持数据脱敏\n- 审计日志追踪\n\n## Q: 可以对接企业微信/飞书吗？\nA: 目前支持通过 MCP 协议对接 Claude Desktop 等AI工具。企业IM对接计划在后续版本中支持。\n\n## Q: 如何部署？\nA: 支持 Docker Compose 一键部署，详细步骤请参考 DEPLOY.md 文档。\n\n## Q: 遇到问题如何反馈？\nA: 在对话界面点击\"踩\"按钮，或联系管理员提交反馈。"),
    # 人事行政
    ("招聘流程手册", "人事行政", "# 招聘流程手册\n\n## 1. 招聘需求确认\n\n### 1.1 需求提报\n- 用人部门填写《人员需求申请表》\n- 部门负责人审批\n- HRBP审核编制和预算\n\n### 1.2 岗位发布\n- HR在招聘平台发布职位\n- 内部推荐渠道同步发布\n- 校园招聘季增加校招渠道\n\n## 2. 简历筛选\n\n### 2.1 初筛标准\n- 学历要求：本科及以上（技术岗硕士优先）\n- 工作经验：按岗位要求\n- 技能匹配度\n\n### 2.2 筛选流程\n1. HR初筛（1个工作日）\n2. 用人部门复筛（2个工作日）\n3. 电话面试（可选）\n\n## 3. 面试流程\n\n### 3.1 面试安排\n- 一面：用人部门技术/业务面试（45分钟）\n- 二面：HR面试（30分钟）\n- 三面（可选）：总监/VP面试\n\n### 3.2 面试评估\n- 技术能力\n- 沟通表达\n- 团队协作\n- 文化匹配度\n\n## 4. 录用决策\n\n1. 面试反馈汇总\n2. 薪资定级\n3. Offer审批\n4. 发放Offer\n5. 背景调查\n6. 入职安排"),
    ("薪酬福利体系", "人事行政", "# 薪酬福利体系\n\n## 1. 薪酬结构\n\n### 1.1 固定薪酬\n- 基本工资：根据岗位职级确定\n- 岗位津贴：特殊岗位补贴\n\n### 1.2 浮动薪酬\n- 绩效奖金：季度发放，与个人KPI挂钩\n- 项目奖金：项目完成后发放\n- 年终奖：1-4个月基本工资\n\n### 1.3 长期激励\n- 股权期权（核心岗位）\n- 利润分享计划\n\n## 2. 福利体系\n\n### 2.1 法定福利\n- 五险一金（按实际工资缴纳）\n- 带薪年假\n- 法定节假日\n\n### 2.2 企业福利\n- 补充商业保险（含家属）\n- 年度体检\n- 免费三餐 + 下午茶\n- 健身房补贴\n- 学习发展基金（5000元/年）\n- 团建活动\n- 节日礼品\n\n### 2.3 特殊福利\n- 弹性工作制\n- 远程办公（每周1天）\n- 带薪病假\n- 生日假（1天）\n- 结婚/生育礼金"),
]

PROMPT_TEMPLATES = [
    ("通用问答", "适用于一般性知识问答场景", 5, 30),
    ("客服助手", "适用于客户服务场景，回答客户咨询", 8, 40),
    ("技术支持", "适用于技术问题排查和解答", 5, 30),
    ("政策咨询", "适用于公司制度和HR政策咨询", 10, 50),
    ("新人引导", "适用于新员工入职引导和培训", 5, 30),
]

AGENTS = [
    ("HR政策顾问", "专业解答公司人事制度、薪酬福利、考勤假期等HR相关政策问题", "你是公司HR政策顾问，专门解答员工关于人事制度、薪酬福利、考勤假期等方面的问题。请基于公司制度文档回答，保持专业友好的语气。"),
    ("技术支持助手", "帮助排查技术问题，提供系统使用指导", "你是技术支持助手，帮助用户解决技术问题和系统使用疑问。回答时给出具体操作步骤，必要时附上相关文档链接。"),
    ("新人入职导航", "为新员工提供入职引导和公司文化介绍", "你是新员工入职导航助手，帮助新员工了解公司文化、制度流程、常用系统等。回答要简洁友好，适合新入职的同事。"),
]

CONVS = [
    ("李先齐", [
        ("公司的考勤制度是什么？", "根据《员工手册2024版》：\n\n**工作时间**：周一至周五 9:00-18:00，午休12:00-13:00，每周双休。\n\n**打卡规定**：\n- 每日需打卡两次：上班（9:00前）和下班（18:00后）\n- 迟到/早退超过30分钟按旷工半天处理\n- 每月允许3次忘打卡补卡机会\n\n**请假制度**：\n- 事假：需提前1天申请，无薪\n- 病假：需提供医院证明，带薪（每年累计不超过15天）\n- 年假：工作满1年享5天，满5年享10天，满10年享15天"),
        ("远程办公怎么申请？", "根据《远程办公管理规定》，申请流程如下：\n\n1. 提前1个工作日在OA系统提交远程办公申请\n2. 部门负责人审批\n3. 审批通过后通知IT部门开通远程访问权限\n\n**适用情况**：\n- 因交通/天气等不可抗力无法到岗\n- 需要集中精力完成紧急项目\n- 医生建议居家休养\n\n**工作要求**：\n- 远程办公期间需在企业微信打卡\n- 核心工作时间（10:00-16:00）必须在线\n- 每日工作结束前在群里汇报当日工作"),
    ]),
    ("张伟", [
        ("怎么上传文档到知识库？", "上传文档到知识库的步骤：\n\n1. 登录KnowFlow系统，进入「文档」页面\n2. 选择对应的知识库\n3. 点击「上传文档」按钮\n4. 选择文件（支持PDF/Word/Excel/Markdown/TXT，单文件最大20MB）\n5. 等待系统自动处理（通常1-5分钟）\n6. 状态显示为「已索引」后即可在对话中查询\n\n**注意事项**：\n- 文档内容质量越高，问答效果越好\n- 建议按主题分类到不同知识库\n- 重复内容会被自动去重"),
        ("API调用怎么认证？", "KnowFlow API使用 JWT (JSON Web Token) 认证：\n\n**获取Token**：\n```\nPOST /api/v1/auth/login\n{\n  \"email\": \"your@email.com\",\n  \"password\": \"your_password\"\n}\n```\n\n**使用Token**：\n在请求头中添加：\n```\nAuthorization: Bearer <your_token>\n```\n\n**Token有效期**：24小时，过期后需重新登录获取。"),
    ]),
    ("李娜", [
        ("公司的年假有多少天？", "根据《员工手册》年假规定：\n\n- 工作满1年：**5天**\n- 工作满5年：**10天**\n- 工作满10年：**15天**\n\n年假需提前3天申请，由部门负责人审批。当年未休完的年假可结转至次年3月31日前使用。"),
        ("五险一金怎么缴纳？", "公司五险一金缴纳标准：\n\n| 险种 | 个人比例 | 公司比例 |\n|------|----------|----------|\n| 养老保险 | 8% | 16% |\n| 医疗保险 | 2% | 8% |\n| 失业保险 | 0.5% | 0.5% |\n| 工伤保险 | 0 | 0.4% |\n| 生育保险 | 0 | 0.8% |\n| 住房公积金 | 12% | 12% |\n\n缴纳基数为上月平均工资，每年7月调整一次。"),
    ]),
    ("王芳", [
        ("面试流程是怎样的？", "根据《招聘流程手册》，面试流程如下：\n\n**一面（技术/业务面）**\n- 面试官：用人部门负责人\n- 时长：约45分钟\n- 内容：专业能力、项目经验\n\n**二面（HR面）**\n- 面试官：HR\n- 时长：约30分钟\n- 内容：职业规划、薪资期望、文化匹配\n\n**三面（可选）**\n- 面试官：总监/VP\n- 适用于高级岗位\n\n面试结果会在3个工作日内通知。"),
    ]),
    ("刘洋", [
        ("新人入职需要准备什么？", "新员工入职需准备以下材料：\n\n**必备材料**：\n1. 身份证原件及复印件\n2. 学历/学位证书原件及复印件\n3. 离职证明（应届生提供三方协议）\n4. 1寸照片2张\n5. 银行卡复印件（工资卡）\n\n**入职当天流程**：\n1. 到HR办公室报到\n2. 提交入职材料\n3. 领取工牌和办公用品\n4. IT开通系统账号\n5. 部门负责人带领熟悉环境\n6. 参加新员工培训"),
    ]),
]

def gen_sql():
    lines = []
    lines.append("-- 模拟数据种子")
    lines.append("BEGIN;\n")

    # Users
    user_ids = {}
    for email, name, role, pwd in USERS:
        uid = h(email)
        user_ids[email] = uid
        hp = pwd_context.hash(pwd)
        lines.append(f"INSERT INTO users (id, email, name, hashed_password, role, is_active, created_at, updated_at) VALUES ('{uid}', '{email}', '{name}', '{hp}', '{role}', true, '{now(-60)}', '{now()}') ON CONFLICT (email) DO NOTHING;")

    # Knowledge Bases
    kb_ids = {}
    admin_id = user_ids["3423554221@qq.com"]
    for name, desc in KBS:
        kid = h(name)
        kb_ids[name] = kid
        lines.append(f"INSERT INTO knowledge_bases (id, name, description, created_by, created_at, updated_at) VALUES ('{kid}', '{name}', '{desc}', '{admin_id}', '{now(-30)}', '{now()}') ON CONFLICT DO NOTHING;")

    # Data Sources
    ds_id = h("local-source")
    lines.append(f"INSERT INTO data_sources (id, name, type, config, status, created_by, created_at) VALUES ('{ds_id}', '本地文件', 'local', '{{}}', 'active', '{admin_id}', '{now(-30)}') ON CONFLICT DO NOTHING;")

    # Documents & Chunks
    doc_ids = []
    for title, kb_name, content in DOCS:
        did = h(title)
        doc_ids.append(did)
        kid = kb_ids.get(kb_name)
        # split content into chunks
        chunks = [p.strip() for p in content.split("\n\n") if p.strip()]
        chunk_data = []
        for i, chunk in enumerate(chunks[:8]):
            cid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{did}-chunk-{i}"))
            safe = chunk.replace("'", "''")
            chunk_data.append(f"('{cid}', '{did}', {i}, '{safe}', NULL, '{{}}', '{now(-25)}')")
        lines.append(f"INSERT INTO documents (id, source_id, kb_id, title, content, content_hash, metadata, status, indexed_at, created_at, updated_at) VALUES ('{did}', '{ds_id}', '{kid}', '{title}', '{content[:500].replace(chr(39), chr(39)*2)}', '{hashlib.md5(content.encode()).hexdigest()}', '{{}}', 'indexed', '{now(-25)}', '{now(-25)}', '{now()}') ON CONFLICT DO NOTHING;")
        if chunk_data:
            lines.append(f"INSERT INTO document_chunks (id, document_id, chunk_index, content, embedding, metadata, created_at) VALUES {','.join(chunk_data)} ON CONFLICT DO NOTHING;")

    # Permissions - all users can read all docs
    for email in [u[0] for u in USERS]:
        uid = user_ids[email]
        for did in doc_ids:
            lines.append(f"INSERT INTO document_permissions (id, document_id, user_id, permission, created_at) VALUES ('{str(uuid.uuid4())}', '{did}', '{uid}', 'read', '{now(-20)}') ON CONFLICT DO NOTHING;")

    # Prompt Templates
    tpl_ids = {}
    for name, desc, top_k, threshold in PROMPT_TEMPLATES:
        tid = h(name)
        tpl_ids[name] = tid
        ctx_prompt = f"请根据以下参考资料回答用户的问题。\n\n参考资料：\n{{context}}\n\n用户问题：{{question}}\n\n请给出准确、详细的回答，并标注信息来源。"
        no_ctx_prompt = "抱歉，当前知识库中没有找到与您问题相关的信息。建议您：\n1. 换个方式描述问题\n2. 联系相关部门获取帮助"
        lines.append(f"INSERT INTO prompt_templates (id, name, description, system_prompt, context_prompt, no_context_prompt, is_active, top_k, threshold, rerank_top_k, created_by, created_at, updated_at) VALUES ('{tid}', '{name}', '{desc}', '你是KnowFlow智能助手。', '{ctx_prompt.replace(chr(39), chr(39)*2)}', '{no_ctx_prompt.replace(chr(39), chr(39)*2)}', true, {top_k}, {threshold}, 3, '{admin_id}', '{now(-20)}', '{now()}') ON CONFLICT DO NOTHING;")

    # Agents
    agent_ids = {}
    for name, desc, prompt in AGENTS:
        aid = h(name)
        agent_ids[name] = aid
        safe_prompt = prompt.replace("'", "''")
        lines.append(f"INSERT INTO agents (id, name, description, system_prompt, top_k, threshold, rerank_top_k, is_active, created_by, created_at, updated_at) VALUES ('{aid}', '{name}', '{desc}', '{safe_prompt}', 5, 30, 3, true, '{admin_id}', '{now(-15)}', '{now()}') ON CONFLICT DO NOTHING;")
        # 关联知识库
        for kb_name in ["公司制度", "人事行政"]:
            kb_id = kb_ids.get(kb_name)
            if kb_id:
                lines.append(f"INSERT INTO agent_knowledge_bases (agent_id, kb_id) VALUES ('{aid}', '{kb_id}') ON CONFLICT DO NOTHING;")

    # Conversations & Messages
    for user_name, msgs in CONVS:
        email = f"{user_name}@company.com" if user_name != "李先齐" else "3423554221@qq.com"
        uid = user_ids.get(email)
        if not uid:
            continue
        conv_id = h(f"conv-{user_name}-{msgs[0][0][:10]}")
        lines.append(f"INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES ('{conv_id}', '{uid}', '{msgs[0][0][:50]}', '{now(-7)}', '{now(-1)}') ON CONFLICT DO NOTHING;")
        for i, (q, a) in enumerate(msgs):
            qid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{conv_id}-q-{i}"))
            aid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{conv_id}-a-{i}"))
            sq = q.replace("'", "''")
            sa = a.replace("'", "''")
            lines.append(f"INSERT INTO messages (id, conversation_id, role, content, sources, created_at) VALUES ('{qid}', '{conv_id}', 'user', '{sq}', '[]', '{now(-7+i)}') ON CONFLICT DO NOTHING;")
            lines.append(f"INSERT INTO messages (id, conversation_id, role, content, sources, created_at) VALUES ('{aid}', '{conv_id}', 'assistant', '{sa}', '[{{\"title\":\"员工手册2024版\",\"score\":0.92}},{{\"title\":\"API接口文档v2.0\",\"score\":0.85}}]', '{now(-7+i+0.01)}') ON CONFLICT DO NOTHING;")

    lines.append("\nCOMMIT;")
    return "\n".join(lines)

if __name__ == "__main__":
    print(gen_sql())
