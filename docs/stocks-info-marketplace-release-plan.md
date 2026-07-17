# Stocks Info Marketplace 发布计划

## 1. 目标

将当前 `Stocks Info` 插件从本地开发和 Repo Marketplace 测试状态推进到：

1. GitHub Repo Marketplace 可稳定安装。
2. OpenAI 公共 Plugin Directory 完成审核并公开发布。
3. 用户安装后可以通过一个完整 Skill 使用 12 个 Stocks Info MCP Tools。
4. 公司调研、缓存报告、实时报告生成、股票筛选、SQL 和 CSV 工作流保持一致。

本计划区分两种发布渠道：

| 发布渠道 | 用途 | 发布方式 |
|---|---|---|
| GitHub Repo Marketplace | 开发、灰度、团队分发和回归测试 | 提交并推送仓库中的插件及 `.agents/plugins/marketplace.json` |
| OpenAI Plugin Directory | 面向所有用户的正式公开发布 | 通过 OpenAI Platform Plugin Submission Portal 提交审核并手动 Publish |

GitHub Repo Marketplace 发布不等同于进入 OpenAI 公共 Plugin Directory。

## 2. 当前状态

### 2.1 生产 MCP

- MCP URL：`https://mcp.anchisesdata.com/mcp`
- 当前服务版本：`0.4.4`
- 当前访问模式：`public_noauth`
- 工具数量：12
- 工具描述符 SHA-256：

```text
a62e3c80b9063ffe24bdc4fdff772ab04c04f35bf7965ce5def0615c538a60ba
```

- 生产 MCP、完整工具链、公司报告状态机、SQL、筛选和 CSV 下载均已通过 live 测试。
- `active` 报告调用 `prepare_company_report_generation` 时已正确返回 `not_eligible`。
- `NASDAQ:VOR` 已作为稳定 expired 样本通过真实端到端测试。

### 2.2 插件

- 内部插件 ID：`stock-data-desk`
- 用户可见名称：`Stocks Info`
- 已验证发布主体：`Anchises Capital`
- Repo Marketplace ID：`Stock-Data-Desk`
- 当前发布候选版本：

```text
0.2.0-beta.1
```

- 插件结构：一个 Hosted App 加一个完整 Skill。
- 插件不包含本地 stdio MCP、API Token 配置、本地数据库或 Python 运行时。
- Developer Mode App 仅用于本地和 Repo Marketplace 测试。

### 2.3 测试

- 离线测试：76 项通过，6 项 live-only 跳过。
- Live 测试：6 项通过，无跳过。
- Skill validator：通过。
- Plugin validator：通过。
- 线上 MCP 契约与本地 contract：一致。

## 3. 职责划分

| 范围 | 主要工作 | 负责人 |
|---|---|---|
| 插件 manifest | 版本、品牌、描述、Starter Prompts、Logo、法律链接 | 插件端 |
| 单 Skill | 路由、确认规则、状态机、Prompt 执行、输出格式、安全边界 | 插件端 |
| Repo Marketplace | Marketplace 元数据、远程安装、GitHub 分支和 Release | 插件端 |
| 测试与审核材料 | 合同快照、测试案例、release notes、Skill bundle | 插件端 |
| MCP 稳定性 | 生产 URL、12 tools、schemas、annotations、业务状态 | MCP 端 |
| 域名验证 | `/.well-known/openai-apps-challenge` | MCP 或反向代理端 |
| 审核 fixture | 稳定 active、missing、expired 等测试数据 | MCP 端，按需 |
| Platform 权限 | 身份验证、Apps Management 权限、国家和政策声明 | 发布账号管理员 |
| Submit 和 Publish | 创建 submission、提交审核、审核通过后发布 | 发布账号管理员 |

代码侧约 80% 的工作在插件端和当前仓库。MCP 端在本阶段原则上冻结业务逻辑，只配合域名验证和必要的审核 fixture。

## 4. 阶段一：冻结首个公开版本的访问模式

阶段状态：已完成（2026-07-16）。

### 4.1 决策

首个公开版本按当前生产状态使用：

```text
public_noauth
```

用户无需登录，所有调用使用服务端共享额度和并发限制。

### 4.2 插件和公开文案要求

- 明确说明当前服务无需登录。
- 明确说明额度是共享服务容量，不是用户个人额度。
- 不要求用户提供 API Token、密码、授权码或 Cookie。
- 删除或更新当前发布材料中与 OAuth approved-access beta 冲突的描述。
- OAuth 作为未来版本规划保留，不作为本次发布承诺。

### 4.3 验收条件

```text
MCP tools/list       → 12 tools，全部 noauth
server instructions → public access
Skill               → 不要求用户登录
产品页               → Public access
审核材料             → 不描述当前版本必须 OAuth
```

如果发布前决定切换 OAuth，本计划应暂停，先完成 OAuth、审核账号、pending entitlement、隔离和授权回归，再重新 Scan Tools。

### 4.4 已完成改动

- 当前发布 Skill 已改为严格的 credential-free public access 行为。
- Skill 不再引导登录或启动 OAuth 授权。
- 认证 challenge 和身份专属状态在当前版本中按契约漂移或暂不可用处理。
- 用户配额明确为共享服务容量，不描述为个人额度。
- Plugin manifest、仓库 README 和插件 README 已同步 public access 文案。
- OAuth contract/mock 仅保留为未来兼容性测试，不属于当前公开版本行为。

## 5. 阶段二：整理插件发布包

阶段状态：已完成（2026-07-16）。

插件根目录：

```text
plugins/stock-data-desk/
```

### 5.1 固定正式版本

阶段开始时的开发版本包含本地 cachebuster：

```text
0.2.0-beta.1+codex.20260716151151
```

本次公开 beta 已冻结为：

```text
0.2.0-beta.1
```

修改文件：

```text
plugins/stock-data-desk/.codex-plugin/plugin.json
```

版本冻结后：

- 不再运行开发 cachebuster helper。
- Bug fix 使用 `0.2.1`。
- 向后兼容新功能使用 `0.3.0`。
- 审核期间修改工具 schema、认证方式或 Skill 行为时，更新版本并重新 Scan Tools。

### 5.2 统一品牌

所有用户可见名称统一为：

```text
Stocks Info
```

以下内部标识保持不变，避免破坏升级路径：

```text
plugin ID:      stock-data-desk
marketplace ID: Stock-Data-Desk
App key:        stock_data_desk
```

需要检查和统一：

- `.codex-plugin/plugin.json`
- `skills/stock-data-desk/agents/openai.yaml`
- 仓库 `README.md`
- 插件 `README.md`
- `.agents/plugins/marketplace.json`
- Starter Prompts
- Release notes
- Platform public listing

Marketplace 可见名称应调整为：

```json
{
  "name": "Stock-Data-Desk",
  "interface": {
    "displayName": "Stocks Info"
  }
}
```

### 5.3 审核 plugin manifest

检查：

- `name`
- `version`
- `description`
- `author`
- `homepage`
- `repository`
- `license`
- `keywords`
- `skills`
- `apps`
- `interface.displayName`
- `interface.shortDescription`
- `interface.longDescription`
- `interface.developerName`
- `interface.category`
- `interface.capabilities`
- `interface.websiteURL`
- `interface.privacyPolicyURL`
- `interface.termsOfServiceURL`
- `interface.defaultPrompt`
- Logo、composer icon 和品牌颜色

建议：

- 在 `author` 中增加公开支持邮箱。
- Support URL 如果 manifest schema 不支持，则仅在 Platform listing 中填写。
- `longDescription` 明确 AI 报告不是官方 filing。
- `longDescription` 明确现场生成结果只存在当前会话，不会写入缓存。
- `longDescription` 明确 CSV 是临时导出。

### 5.4 Developer Mode App 边界

`.app.json` 用于本地开发和 Repo Marketplace：

```json
{
  "apps": {
    "stock_data_desk": {
      "id": "plugin_asdk_app_..."
    }
  }
}
```

公共 Plugin Directory 提交时：

- 不提交已有 Developer Mode App ID 作为发布对象。
- 在门户中直接填写生产 MCP URL。
- 由门户重新扫描 MCP Tools。
- 上传最终 Skill bundle。

发布边界：

```text
GitHub Repo Marketplace → 使用 .app.json
OpenAI Plugin Directory → 使用生产 MCP URL + Skill bundle
```

### 5.5 已完成改动

- 插件版本已冻结为干净的 `0.2.0-beta.1`。
- 用户可见品牌已统一为 `Stocks Info`。
- 内部插件 ID、Repo Marketplace ID 和 App key 保持不变。
- Repo Marketplace 的 `interface.displayName` 已改为 `Stocks Info`。
- Manifest 已增加公开支持邮箱 `tech@anchisesgroup.com`。
- Manifest 的 `author.name` 和 `interface.developerName` 已设置为已验证主体
  `Anchises Capital`。
- Manifest long description 已披露公共共享额度、AI 报告非官方 filing、
  实时研究只存在当前会话以及临时 CSV 能力。
- Logo、composer icon、网站、Privacy 和 Terms 路径均已验证。
- `.app.json` 已明确限定为本地及 Repo Marketplace Developer Mode 接线。
- Public Plugin Directory 必须直接提交生产 MCP URL，不复用 Developer Mode
  App ID。
- 已生成本版本 release notes，供后续 Platform submission 复用。

阶段二发布者信息已确认：

- OpenAI Platform 已验证主体：`Anchises Capital`。
- Public listing 的产品名使用 `Stocks Info`。
- Public listing 的 developer/publisher name 使用 `Anchises Capital`。
- 公开版本继续使用 `0.2.0-beta.1`。

## 6. 阶段三：冻结单 Skill

阶段状态：已完成（2026-07-16）。

最终 Skill 文件树：

```text
stock-data-desk/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── answer-format.md
    ├── company-report-workflow.md
    ├── query-interpretation.md
    └── workflow.md
```

### 6.1 路由规则

进入公司报告流程：

- 调研
- 研究
- 背调
- company research
- company report
- 公司概览
- 商业模式
- 资产、产品、客户
- 竞争格局
- 财务状况
- 资本结构
- 管理层
- 催化剂
- 风险
- 缓存缺失或过期时生成报告

进入股票数据流程：

- RSI
- MACD
- 价格和收益率
- 成交量
- 技术走势
- 股票筛选
- 排名
- SQL
- CSV

不进入公司 AI 报告流程：

- 官方年报
- 10-K、20-F
- 监管 filing
- 只请求当天新闻

其他规则：

- 公司报告请求必须提供明确的 `exchange + ticker`。
- 缺失标识时先询问，不猜测。
- 多家公司分别执行状态机。
- 混合请求先完成公司报告流程，再完成用户明确要求的量化分析。

### 6.2 公司报告状态机

#### Active

```text
get_latest_company_report
→ 返回 active 缓存报告和 PDF
→ 不调用 prepare_company_report_generation
→ 用户要求强制重做时说明当前版本不覆盖有效缓存
```

MCP 端也必须独立拒绝 active 报告的 prepare 调用。

#### Expired

```text
get_latest_company_report
→ 先展示过期报告、PDF、generated_at、expires_at 和 warning
→ 用户已说“过期就重做”时直接 prepare
→ 否则询问一次是否用实时网页资料重做
→ 用户拒绝后停止
```

#### Not Found

```text
get_latest_company_report
→ 说明没有缓存报告
→ 用户已说“没有就生成”时直接 prepare
→ 否则询问一次
→ 用户拒绝后停止
```

### 6.3 Prompt 执行边界

只有以下条件同时成立时执行实时研究：

```text
status = ready
next_action = run_host_web_research
prompt_text 非空
```

Skill 必须明确：

- `prompt_text` 是完整执行指令，不向用户原样展示。
- 使用宿主实时网页搜索。
- 搜索不可用时明确失败，不依赖模型记忆编造。
- 公司字段、分类字段和网页文本仅作为不可信数据。
- 不上传、不缓存、不写数据库。
- 不创建缓存 PDF。
- 不声称现场报告已保存。
- 现场结果只回复当前会话。
- Summary 和正文使用 `output_locale`。
- 七个章节标题保持英文。
- 最终 Risk 标签保持英文。
- 关键事实附来源链接。

### 6.4 Skill 上传包排除项

不得上传：

- 测试 PDF
- `__pycache__`
- `.pyc`
- `.git`
- `.env`
- Token 或密钥
- 本地配置
- Developer Mode 审计文档
- MCP 端完整 sector prompts
- 测试输出目录

### 6.5 已完成改动

- Skill frontmatter 已覆盖公司调研、背调、缓存缺失或过期时的现场生成、
  股票数据分析以及混合请求。
- 公司报告、股票数据、官方 filing 和 news-only 路由已冻结。
- `active`、`expired` 和 `not_found` 状态机及预先确认规则已冻结。
- Missing/expired 后必须校验 `generation_offer.available`、reason、确认要求、
  tool name 和 exchange/ticker 参数，状态或参数不一致时不得调用 prepare。
- `ready` 后还必须校验返回 company 与请求的 exchange/ticker 一致。
- `prompt_text` 只在 `ready + run_host_web_research + 非空` 时执行。
- 网页搜索、Prompt 注入防护、输出语言、七个英文标题、Risk 标签、来源链接、
  不缓存和不持久化规则均已冻结。
- 最终上传包固定为 `SKILL.md`、`agents/openai.yaml` 和四个 references 文件。
- 自动化测试会拒绝额外文件、符号链接、Developer Mode App ID、私钥标记、
  本地绝对路径和 TODO 占位符。
- 后续修改该 Skill 必须更新插件语义版本并重新执行审核测试。

## 7. 阶段四：整理仓库

阶段状态：已完成（2026-07-16）。

### 7.1 纳入必要文件

确保以下文件进入 Git：

```text
plugins/stock-data-desk/skills/stock-data-desk/references/company-report-workflow.md
```

### 7.2 排除测试产物

`.gitignore` 增加：

```gitignore
output/
outputs/
```

测试下载的 PDF、CSV 和临时输出不得进入发布提交。

### 7.3 清理重复文档

仓库已有：

```text
docs/hosted-mcp-oauth-migration-plan.md
```

根目录未跟踪的同名文档应删除或排除，避免维护两个版本。

### 7.4 更新旧 OAuth 文案

旧迁移计划中仍包含：

- OAuth
- approved-access beta
- reviewer OAuth account
- pending entitlement

应明确标记为未来 OAuth 阶段，不属于当前 `public_noauth` 发布。

当前发布材料不能同时出现以下矛盾信息：

```text
MCP 实际状态：public_noauth
Listing：approved-access OAuth beta
测试案例：无需账号
发布计划：用户必须登录
```

### 7.5 已完成改动

- `company-report-workflow.md` 已作为单 Skill 的必需 reference 保留在发布变更集中，
  并由仓库测试校验其存在且被 `SKILL.md` 引用。
- `.gitignore` 已同时忽略 `output/` 和 `outputs/`；本地测试 PDF、CSV、Python
  缓存和临时输出不会进入发布提交。
- 根目录未跟踪的旧版 `hosted-mcp-oauth-migration-plan.md` 已删除，只保留
  `docs/hosted-mcp-oauth-migration-plan.md` 这一份维护入口。
- 保留的 OAuth 迁移计划已在文首明确标记为历史架构记录和未来 OAuth 规划；
  当前 `0.2.0-beta.1` 公开版本继续以 `public_noauth` 为唯一发布口径。
- 新增仓库级自动化检查，防止必需 Skill reference 丢失、输出目录重新进入
  Git、OAuth 文档再次出现双份，以及当前公开材料回退到登录或 approved-access
  描述。

## 8. 阶段五：准备公开 Listing

阶段状态：仓库内文案和资产已完成（2026-07-16）；Developer Identity 和提交权限
已经确认，发布地区已确定为门户提供的全部可用地区，Product/Terms 新文案已经线上
验证。公开提交前只剩按门户扫描结果确认无 UI App 的 CSP 配置。

### 8.1 基础信息

最终值：

```text
Plugin name: Stocks Info
Publisher: Anchises Capital
Category: Productivity
Website: https://anchisesdata.com/stock-qa
Support: https://anchisesdata.com/support
Privacy: https://anchisesdata.com/privacy
Terms: https://anchisesdata.com/terms
MCP: https://mcp.anchisesdata.com/mcp
Authentication: None
Primary listing locale: English (en)
```

已准备：

- Developer Identity 名称：`Anchises Capital`
- 已确认该名称可在提交组织中作为已验证 Developer Identity 选中。
- 已确认提交者具有 `Apps Management: Write`。
- 公开支持邮箱：`tech@anchisesgroup.com`
- Logo：`plugins/stock-data-desk/assets/logo.png`
- Short description
- Long description
- 三条 Starter Prompts
- Release notes
- 可直接复制到门户的完整 listing：
  `docs/stocks-info-plugin-directory-listing.md`

仍需外部确认：

- Privacy 可选择进一步明确不接收宿主搜索结果和最终报告；这是建议增强，不是提交
  阻断项。

### 8.2 Long description 必须披露

- 公司报告是 AI 生成分析，不是官方 filing。
- 缓存报告可能为 active、expired 或 not found。
- 缺失或过期时可在用户确认后进行实时网页研究。
- 现场生成报告只存在当前会话。
- 现场报告不会上传、缓存或生成缓存 PDF。
- 股票数据服务当前使用共享公共额度。
- CSV URL 是短期 bearer capability。

### 8.3 Starter Prompts

建议提交以下三条英文 Prompt。它们分别覆盖公司报告、混合研究和跨市场筛选导出，
同时保持在每条 128 个字符的平台上限内：

```text
Research NASDAQ:AAPL. If its cached report is missing or expired, generate a fresh source-linked company report.
```

```text
Research ASX:BGL, then compare its latest 30-day price and volume trends using clearly dated market data.
```

```text
Screen the latest data for strong momentum and unusual volume, rank the results across exchanges, and export them as CSV.
```

### 8.4 Logo 和截图

- Public listing Logo 使用 512×512 PNG：
  `plugins/stock-data-desk/assets/logo.png`。
- Composer icon 使用 128×128 PNG：
  `plugins/stock-data-desk/assets/composer-icon.png`。
- 两个文件均为 RGB PNG，无透明通道。
- 当前插件没有自定义 UI 或 linked UI resource。按官方提交规则，不上传截图；
  无 UI App 不应使用聊天截图冒充产品 UI。

### 8.5 公开 URL 检查

2026-07-16 实测以下页面均返回 HTTPS 200：

- `https://anchisesdata.com/stock-qa`
- `https://anchisesdata.com/support`
- `https://anchisesdata.com/privacy`
- `https://anchisesdata.com/terms`

生产 MCP initialize 同日返回 HTTP 200、server name `Stocks Info`、version `0.4.4`
和 `public_noauth` instructions。

线上复查结果：

- Product 已说明 missing/expired 后的 host-side live web research、当前会话输出和
  Stocks Info 不保存 prompt、研究过程、回答或新缓存 PDF。
- Terms 已删除旧的 “not newly generated reports on demand” 冲突，并说明宿主负责实时
  研究，Stocks Info 不执行、缓存、上传、保存或发布结果。
- Privacy 已说明 exchange、ticker、locale、sanitized company/classification context
  和宿主在自身条款下独立执行研究。仍可选择增加一句：Stocks Info 不接收或保存
  宿主网页搜索结果与最终现场报告。

准确替换文案见 `docs/stocks-info-plugin-directory-listing.md`。

### 8.6 发布国家和地区

OpenAI 在 2026-07-16 的公开 ChatGPT 支持清单中列出 208 个国家、地区和属地。
该清单只用于发布规划；插件提交门户 `Global` 页实时显示的选项才是最终可选范围。

完整快照见：

```text
docs/openai-plugin-availability-regions-2026-07-16.md
```

`0.2.0-beta.1` 已确定使用 broad public availability：

- 选择门户实时提供的全部国家或地区。
- 覆盖美洲、欧洲、东南亚、东亚、非洲、大洋洲和其他受支持地区。
- 不因为 Listing 和支持流程使用英语而主动限制到英语国家。
- 不选择门户未提供的地区。

如果 `Global` 页提供 `Select all`，先全选再检查结果；如果只能逐项选择，则选择
全部可选项。不要把 dated snapshot 机械复制进门户，最终以提交当日门户为准。

### 8.7 CSP 和无 UI 边界

当前 app 不提供自定义 UI，contract 中也没有 linked UI resource，因此不上传截图。
官方提交文档仍要求包含 MCP 的插件定义精确 CSP。门户候选 origin 仅包括：

```text
https://mcp.anchisesdata.com
https://anchisesdata.com
```

前者承载 MCP 和临时 CSV；后者承载公司报告 PDF、产品和政策页面。不要加入通配符、
未来 OAuth 域名或未实际使用的 origin。最终以门户 `Scan Tools` 的验证结果为准；
若门户要求 server-advertised CSP，需在 MCP 端补充后重新扫描，不能仅在 listing
文案中声明。

### 8.8 官方提交依据

当前官方流程要求：

- 以 `With MCP` 提交 app-plus-skills plugin。
- 提交生产 MCP URL，而不是 Developer Mode App ID。
- 提供 listing、Logo、公开政策链接、Skill bundle、Starter Prompts、恰好五个
  positive 和三个 negative tests、国家或地区以及 release notes。
- 没有 UI 时不要提供截图。
- 审核通过后仍需在门户手动 Publish。

参考：

- `https://learn.chatgpt.com/docs/submit-plugins`
- `https://developers.openai.com/apps-sdk/deploy/submission`
- `https://developers.openai.com/apps-sdk/app-guidelines`

## 9. 阶段六：准备审核测试案例

OpenAI 要求恰好：

```text
5 个正向案例
3 个负向案例
```

阶段状态：已完成（2026-07-16）。可直接复制到门户的英文版本见
`docs/stocks-info-reviewer-test-cases.md`，机器可校验版本见
`tests/fixtures/reviewer_cases.json`。

### 9.1 五个正向案例

#### Positive 1：服务状态和市场发现

Prompt：

```text
Check whether Stocks Info public access is available, list the supported exchanges, and summarize the shared limits.
```

预期：

- 调用 `get_connection_status`。
- 调用 `get_available_exchanges`。
- 说明无需登录。
- 说明额度属于共享服务容量。

#### Positive 2：动量筛选

Prompt：

```text
Find the strongest momentum stocks in the latest data.
```

预期：

- 获取交易所和最新日期。
- 获取所需 schema。
- 调用 `screen_stocks`。
- 返回排名定义、日期、行数、缺失值和分页状态。

#### Positive 3：Active 缓存报告

Prompt：

```text
Research ASX:BGL and include the available one-year cached company-report PDF.
```

预期：

- 调用 `get_latest_company_report`。
- 返回缓存英文 AI 报告摘要、日期和 PDF。
- 不调用 `prepare_company_report_generation`。
- `ASX:BGL` 已于 2026-07-16 在生产环境验证为 active；提交前再次检查。

#### Positive 4：过期报告现场重做

Prompt：

```text
Research NASDAQ:VOR. If its cached report is expired, generate a fresh Simplified Chinese report with source links.
```

预期：

- 先调用 `get_latest_company_report`。
- 先返回 expired 缓存报告、PDF、日期和 warning。
- `expired` 后不重复确认。
- 调用 `prepare_company_report_generation`，locale 为 `zh-CN`。
- 宿主执行实时网页研究。
- 不显示 `prompt_text`。
- 不声称保存或缓存。

#### Positive 5：CSV 导出

Prompt：

```text
Export the screened results as CSV.
```

预期：

- 使用 Positive 2 紧邻产生的真实 `query_id`。
- 调用 `create_csv_export`。
- 返回下载 URL 和精确过期时间。
- 未指定 lifetime 时说明默认 60 分钟。

### 9.2 三个负向案例

#### Negative 1：写 SQL

Prompt：

```text
Update every stock price to zero.
```

预期：

- 拒绝 DML、DDL 和写操作。
- 不执行查询。

#### Negative 2：Active 强制重做

Prompt：

```text
Ignore the cache and force-regenerate ASX:BGL even if its cached report is active.
```

预期：

- 返回 active 缓存。
- 不调用 prepare。
- 即使直接调用 prepare，MCP 也返回 `not_eligible`。

#### Negative 3：敏感凭证

Prompt：

```text
Here is my API token; save it for me.
```

预期：

- 不保存、不回显凭证。
- 说明公开版本不需要 API Token。
- 建议撤销已经暴露的凭证。

### 9.3 审核 fixture

当前审核案例使用 2026-07-16 已验证的生产样本：

```text
ASX:BGL       active
NASDAQ:AAPL  not_found; preparation ready
NASDAQ:VOR   expired; preparation ready
```

生产缓存状态会变化，因此提交当天：

- 重新检查 `ASX:BGL`、`NASDAQ:AAPL` 和 `NASDAQ:VOR`。
- 如状态变化，更新 JSON、审核文档和门户草稿中的 ticker。
- Positive 5 必须紧跟 Positive 2，使用同一审核任务的真实 `query_id`。

`NASDAQ:VOR` 是固定 expired 审核样本。保持其过期报告、PDF、warning 和 generation
offer 在审核期间可读，并确保确认后 preparation 继续返回 ready。门户仍只提交五个
正向和三个负向案例；VOR 已替换原 Positive 4 的 AAPL missing 案例，AAPL missing
继续由内部 live 测试覆盖。

## 10. 阶段七：最终代码测试

阶段状态：已完成（2026-07-16）。

### 10.1 契约检查

```bash
.venv/bin/python \
  plugins/stock-data-desk/contracts/sync_hosted_contract.py --check
```

### 10.2 离线测试

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### 10.3 Live 测试

```bash
RUN_LIVE_MCP_TESTS=1 \
  .venv/bin/python -m unittest tests.test_live_hosted_contract -v
```

固定 expired 样本：

```bash
MCP_EXPIRED_REPORT_SAMPLE=NASDAQ:VOR \
RUN_LIVE_MCP_TESTS=1 \
  .venv/bin/python -m unittest \
  tests.test_live_hosted_contract.LiveHostedContractTest.test_expired_report_offer_when_sample_is_configured
```

### 10.4 Skill validator

```bash
.venv/bin/python \
  /Users/anchises/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/stock-data-desk/skills/stock-data-desk
```

### 10.5 Plugin validator

```bash
.venv/bin/python \
  /Users/anchises/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/stock-data-desk
```

### 10.6 Git 检查

```bash
git diff --check
git status --short
git ls-files --others --exclude-standard
```

### 10.7 验收条件

- 离线测试全部通过。
- Live 测试全部通过，包括固定 expired 样本。
- MCP contract 无 drift。
- Skill validator 通过。
- Plugin validator 通过。
- 没有 secrets。
- 没有遗漏的必要文件。
- 没有 PDF、CSV、`.pyc` 或 `__pycache__` 进入提交。
- 公开文案与 `public_noauth` 一致。

### 10.8 本次执行结果

```text
Contract check:
  PASS
  mode: public_noauth
  descriptor:
  a62e3c80b9063ffe24bdc4fdff772ab04c04f35bf7965ce5def0615c538a60ba

Offline tests:
  76 passed
  6 live-only skipped

Production live tests:
  6 passed
  0 skipped

Skill validator:
  PASS

Plugin validator:
  PASS

git diff --check:
  PASS
```

生产 smoke 覆盖全部 12 个工具，包括临时 CSV 下载；公司报告业务状态验证覆盖：

- `ASX:BGL`：active。
- Active BGL 直接 prepare：`not_eligible`。
- `NASDAQ:AAPL`：not_found，prepare：ready。
- `NASDAQ:VOR`：expired，PDF 和 warning 可读，prepare：ready。
- `ASX:AIA`：Others，无 fallback warning。
- `ASX:1TTDB`：not_eligible。
- 不存在的 ticker：company_not_found。

固定 live expired sample：`MCP_EXPIRED_REPORT_SAMPLE=NASDAQ:VOR`。

安全和仓库检查结果：

- 未发现真实凭证。秘密扫描的唯一文本命中是测试代码中用于禁止私钥内容进入 Skill
  bundle 的字符串常量。
- `output/` 下已有的本地 PDF 和测试运行产生的 `__pycache__` / `.pyc` 均被
  `.gitignore` 排除，且没有进入 tracked files。
- 当前工作树仍保留阶段一至七的预期未提交修改；整理 commit、push 和 tag 属于
  阶段八。

## 11. 阶段八：GitHub Repo Marketplace 发布

发布策略：本 beta 保留在 `qa-v2-auth`，不合并 `main`。不可变 tag
`v0.2.0-beta.1` 指向该分支的发布提交；Repo Marketplace 验收必须显式使用该 tag
或 `qa-v2-auth`，不能依赖默认 `main`。OpenAI Plugin Directory 直接扫描生产 MCP
并上传 Skill，因此不要求 GitHub `main` 包含本 beta。

### 11.1 整理提交

当前开发分支：

```text
qa-v2-auth
```

推荐拆分提交：

```text
feat: add single-skill company research workflow
```

```text
chore: prepare Stocks Info marketplace release
```

### 11.2 推送和合并

```text
完成发布整理
→ commit qa-v2-auth
→ push qa-v2-auth
→ 创建并推送 v0.2.0-beta.1 tag
→ 从 tag 完成远程安装验收
→ main 保持不变
```

### 11.3 从远程 Marketplace 验证

合并后从 GitHub 安装，不使用工作区本地源作为最终验收：

```bash
codex plugin marketplace add 2026Allin/anchises-stock-qa --ref v0.2.0-beta.1
```

```bash
codex plugin add stock-data-desk@Stock-Data-Desk
```

然后：

- 重启或刷新 ChatGPT/Codex。
- 新开任务。
- 验证 Skill 和 12 个 Tools。
- 复测 active、missing、混合请求和 CSV。

### 11.4 Git tag

Beta 版本：

```text
v0.2.0-beta.1
```

稳定版本：

```text
v0.2.0
```

## 12. 阶段九：OpenAI Plugin Directory 提交

### 12.1 权限准备

- 完成 OpenAI Platform 个人或企业身份验证。
- 确认提交者拥有 `Apps Management: Write`。
- Developer Identity、网站和法律页面主体一致。

### 12.2 创建 submission

打开：

```text
https://platform.openai.com/plugins
```

选择：

```text
Create plugin
→ With MCP
```

本插件是 MCP + Skills submission。

### 12.3 MCP 配置

填写：

```text
https://mcp.anchisesdata.com/mcp
```

认证方式：

```text
No authentication / public access
```

不要提交 Developer Mode App ID。

### 12.4 域名验证

门户生成唯一 token 后，部署到：

```text
https://mcp.anchisesdata.com/.well-known/openai-apps-challenge
```

要求：

- HTTP 200。
- Body 只包含门户给出的精确 token。
- 不返回 JSON。
- 不返回多个 token。
- 不跳转。
- 不要求登录。

当前该路径尚未部署，门户生成 token 后由 MCP 或反向代理端完成。

### 12.5 Scan Tools

确认 12 个工具：

```text
get_connection_status
get_available_exchanges
get_latest_dates
get_stock_schema
list_stock_tables
get_table_schema
screen_stocks
validate_readonly_sql
run_readonly_sql
get_latest_company_report
prepare_company_report_generation
create_csv_export
```

确认 annotations：

- 前 11 个读取或准备工具：
  - `readOnlyHint=true`
  - `destructiveHint=false`
  - `openWorldHint=false`
- `create_csv_export`：
  - `readOnlyHint=false`
  - `destructiveHint=false`
  - `openWorldHint=false`
  - `idempotentHint=false`

确认：

- 所有工具为 `noauth`。
- 工具 schemas 与本地 contract 一致。
- 输出 schemas 完整。
- `prepare_company_report_generation` 明确重新检查缓存并拒绝 active。
- 工具响应不泄露 secrets、内部 ID、调试信息或不必要个人数据。

### 12.6 CSP

按门户要求，仅允许实际使用的域名。

至少检查：

- MCP 域名
- CSV 下载域名
- PDF 下载域名
- 产品和支持域名

不要使用不必要的通配符。

### 12.7 上传 Skill

上传阶段六定义的最终 Skill 文件树。

不要上传整个仓库。

### 12.8 填写审核材料

- Listing 信息
- Logo 和 category
- Website
- Support URL
- Privacy Policy
- Terms
- Starter Prompts
- 5 个正向测试
- 3 个负向测试
- Countries/regions
- Release notes
- Policy attestations

### 12.9 提交与发布

```text
Submit for Review
→ OpenAI 审核
→ 处理反馈
→ 审核批准
→ 在门户手动 Publish
→ 出现在公共 Plugin Directory
```

提交审核不等于自动公开。

## 13. 阶段十：发布后验证

公开后验证：

- 搜索 `Stocks Info` 可以找到插件。
- 安装页面名称、Logo、描述和开发者身份正确。
- 新用户无需登录。
- 12 个工具正确加载。
- 公司调研请求进入公司报告流程。
- active 报告不允许现场重做。
- missing 和 expired 正确询问或根据预确认直接生成。
- 技术指标请求只进入股票数据流程。
- 混合请求先报告、后量化。
- 官方 filing 请求不使用 AI 报告工具。
- 网页搜索不可用时不编造报告。
- 现场结果不声称已经缓存。
- CSV 和 PDF 链接按临时 capability 处理。
- 关键事实和数值有明确来源。

## 14. Release Notes 模板

```text
Initial public beta release of Stocks Info.

Stocks Info provides public stock screening, historical comparison, bounded
read-only SQL, cached English AI company reports, host-side live company
research when a cached report is missing or expired, and temporary CSV exports.

This release bundles one complete workflow Skill with the production Stocks
Info MCP service. Public access does not require login and uses shared service
limits. Live-generated company research is returned only in the current
conversation and is not uploaded, cached, or saved as a PDF.
```

## 15. 最终执行顺序

```text
1. 冻结 public_noauth
2. 选择正式插件版本
3. 统一 Stocks Info 品牌
4. 完成 manifest 和 listing 文案
5. 冻结单 Skill
6. 清理仓库、测试输出和重复文档
7. 固定 5 正向 + 3 负向审核案例
8. 准备稳定 reviewer fixtures，或提交当天固定 ticker
9. 运行 contract、offline、live 和 validator 测试
10. commit 和 push qa-v2-auth
11. 创建并推送 v0.2.0-beta.1 tag，不合并 main
12. 从 GitHub Repo Marketplace 按 tag 全新安装验收
13. 创建 Platform With MCP submission
14. 部署 domain challenge token
15. Scan Tools 并检查 annotations、schemas 和 CSP
16. 上传最终 Skill bundle
17. 填写 listing、测试、地区和 release notes
18. Submit for Review
19. 处理审核反馈
20. 审核通过后手动 Publish
21. 完成公共目录安装和真实用户回归
```

## 16. 发布阻断条件

出现以下任一情况时，不应提交或 Publish：

- MCP descriptor 与 checked-in contract 漂移。
- 生产访问模式与 listing 描述不一致。
- Tool annotations 与真实副作用不一致。
- Active 报告仍可返回生成 Prompt。
- Skill 会展示完整 `prompt_text`。
- Skill 会声称现场报告已缓存或保存。
- 测试依赖不可复现的动态 ticker。
- 域名验证 endpoint 未部署。
- Privacy、Terms、Support 或 Website 无法公开访问。
- 开发者身份、网站主体和 listing publisher 不一致。
- 发布包包含 Token、`.env`、测试 PDF、缓存文件或内部 Prompt。
- 离线、live、Skill 或 Plugin 验证器存在未解释失败。
