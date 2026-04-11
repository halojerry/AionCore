# 01 - 公共类型与 Trait

## 概述

定义跨 crate 共享的基础类型、业务枚举、通用 trait 和 API DTO。按职责划分到三个 crate：

| Crate | 定位 | 内容 |
|-------|------|------|
| `aionui-common` | 最底层基础 crate，零业务逻辑 | 错误类型、分页、时间戳、ID 生成、加密工具 |
| `aionui-api-types` | HTTP/WS 请求响应 DTO | API 响应信封、各模块的请求/响应结构体 |
| `aionui-db` | 数据库模型 | 表映射结构体、Repository trait |

**原则**：类型归属取决于"谁依赖谁"——如果只有一个模块使用，留在该模块内部；两个以上模块共用，才提升到公共 crate。

---

## A. aionui-common — 基础类型

### A.1 统一错误类型

所有 crate 共享的错误定义。替代原实现中 `IQueryResult<T>` 包装和不一致的 `message`/`error` 字段。

```rust
/// Application-level error with HTTP status code and machine-readable code.
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Bad request: {0}")]
    BadRequest(String),

    #[error("Unauthorized: {0}")]
    Unauthorized(String),

    #[error("Forbidden: {0}")]
    Forbidden(String),

    #[error("Conflict: {0}")]
    Conflict(String),

    #[error("Rate limited")]
    RateLimited,

    #[error("Internal error: {0}")]
    Internal(String),

    #[error("Bad gateway: {0}")]
    BadGateway(String),

    #[error("Request timeout: {0}")]
    Timeout(String),
}
```

每个 variant 映射到 HTTP 状态码（404 / 400 / 401 / 403 / 409 / 429 / 500 / 502 / 408），通过 `impl IntoResponse for AppError` 自动转换为 JSON 错误响应。

> **设计决策**：原实现中数据库操作返回 `{ success, data?, error? }` 包装（`IQueryResult<T>`），调用方需手工检查 `success` 字段。Rust 中直接使用 `Result<T, AppError>`，编译器强制处理错误，`IQueryResult<T>` 不再迁移。

### A.2 分页

```rust
/// Universal paginated result. Used by conversation, message, and other list APIs.
pub struct PaginatedResult<T> {
    pub items: Vec<T>,
    pub total: u64,
    pub has_more: bool,
}
```

> 来源：模块 02 的 `IPaginatedResult<T>` 和 `PaginatedResult<T>` 合并为单一类型。原实现中存在两种分页结构（带 page/pageSize 和不带的），统一为一种。

### A.3 ID 生成

```rust
/// Generate a time-ordered globally unique ID (UUID v7).
pub fn generate_id() -> String;

/// Generate a prefixed ID (e.g., "cron_<uuid>", "mcp_<uuid>").
pub fn generate_prefixed_id(prefix: &str) -> String;
```

> **设计决策**：原实现使用 `user_${Date.now()}` 等格式。改用 UUID v7（时间有序 + 全局唯一），通过 `uuid` crate 生成。

### A.4 时间戳

```rust
/// Unix timestamp in milliseconds (consistent with original TS implementation).
pub type TimestampMs = i64;

/// Get current timestamp in milliseconds.
pub fn now_ms() -> TimestampMs;
```

### A.5 加密工具

```rust
/// Encrypt a string value using AES-GCM.
pub fn encrypt_string(plaintext: &str, key: &[u8]) -> Result<String, AppError>;

/// Decrypt an AES-GCM encrypted string.
pub fn decrypt_string(ciphertext: &str, key: &[u8]) -> Result<String, AppError>;
```

> 来源：模块 02、06、09 中均使用 AES 加密存储敏感数据（API Key、通道凭据、远程 Agent Token）。统一到 `aionui-common` 避免重复实现。

---

## B. aionui-common — 业务枚举

以下枚举被两个以上模块引用，归入 `aionui-common`。

### B.1 AgentType — 会话/Agent 类型

```rust
/// Type of AI agent backend. Used by conversation, AI agent, cron, channel, team modules.
pub enum AgentType {
    Gemini,
    Acp,
    OpenclawGateway,
    Nanobot,
    Remote,
    Aionrs,
}
```

> 来源：模块 05（会话创建）、06（Agent 实现）、09（通道 Agent 选择）、10（团队 Agent 创建）、11（定时任务执行）。

### B.2 AcpBackend — ACP 子后端标识

```rust
/// ACP sub-backend identifier. 20+ variants for different CLI-based AI backends.
pub enum AcpBackend {
    Claude,
    Gemini,
    Qwen,
    IFlow,
    Codex,
    CodeBuddy,
    Droid,
    Goose,
    Auggie,
    Kimi,
    OpenCode,
    Copilot,
    Qoder,
    OpenclawGateway,
    Vibe,
    Nanobot,
    Cursor,
    Kiro,
    Remote,
    Aionrs,
    Custom,
}
```

> 来源：模块 05（ACP 会话创建）、06（ACP Agent 实现、YOLO 模式映射）、09（通道 Agent 配置）。

### B.3 ConversationStatus — 会话运行时状态

```rust
/// Runtime status of a conversation.
pub enum ConversationStatus {
    Pending,
    Running,
    Finished,
}
```

> 来源：模块 02（数据库 CHECK 约束）、05（会话状态管理）、06（Agent 状态查询、空闲超时检测）。

### B.4 ConversationSource — 会话来源

```rust
/// Origin of a conversation.
pub enum ConversationSource {
    Aionui,
    Telegram,
    Lark,
    Dingtalk,
    Weixin,
}
```

> 来源：模块 05（会话创建/筛选）、09（通道消息路由、per-chat 隔离）。

### B.5 MessageType — 消息类型

```rust
/// Type discriminant for messages in a conversation.
pub enum MessageType {
    Text,
    Tips,
    ToolCall,
    ToolGroup,
    AgentStatus,
    AcpPermission,
    AcpToolCall,
    CodexPermission,
    CodexToolCall,
    Plan,
    Thinking,
    AvailableCommands,
    SkillSuggest,
    CronTrigger,
}
```

> 来源：模块 02（消息表类型字段）、05（流式消息推送）、06（Agent 消息后处理）、11（cron_trigger / skill_suggest 注入）。

### B.6 MessagePosition — 消息显示位置

```rust
/// Display position of a message in the chat UI.
pub enum MessagePosition {
    /// User message (right side)
    Right,
    /// AI response (left side)
    Left,
    /// System notification (center)
    Center,
    /// Popup notification
    Pop,
}
```

### B.7 MessageStatus — 消息状态

```rust
/// Processing status of a message.
pub enum MessageStatus {
    Finish,
    Pending,
    Error,
    Work,
}
```

### B.8 ProtocolType — API 协议类型

```rust
/// LLM API protocol type. Used by model provider detection and configuration.
pub enum ProtocolType {
    OpenAI,
    Anthropic,
    Gemini,
    Unknown,
}
```

> 来源：模块 04（协议检测）、06（API 客户端工厂）。

### B.9 RemoteAgentProtocol — 远程 Agent 协议

```rust
pub enum RemoteAgentProtocol {
    OpenClaw,
    ZeroClaw,
    Acp,
}
```

### B.10 RemoteAgentAuthType — 远程 Agent 认证方式

```rust
pub enum RemoteAgentAuthType {
    Bearer,
    Password,
    None,
}
```

### B.11 RemoteAgentStatus — 远程 Agent 连接状态

```rust
pub enum RemoteAgentStatus {
    Unknown,
    Connected,
    Pending,
    Error,
}
```

> B.9–B.11 来源：模块 02（数据库表）、06（Remote Agent 管理 REST API 和连接状态更新）。

### B.12 AgentKillReason — Agent 终止原因

```rust
pub enum AgentKillReason {
    IdleTimeout,
}
```

### B.13 PreviewContentType — 预览内容类型

```rust
pub enum PreviewContentType {
    Markdown,
    Diff,
    Code,
    Html,
    Pdf,
    Ppt,
    Word,
    Excel,
    Image,
    Url,
}
```

> 来源：模块 16（预览快照历史），前端也需使用。

### B.14 FileChangeOperation — 文件变更操作

```rust
pub enum FileChangeOperation {
    Create,
    Modify,
    Delete,
}
```

> 来源：模块 08（工作区快照）、07（文件变更事件广播）。

---

## C. aionui-common — 业务结构体

### C.1 ProviderWithModel — 模型选择配置

```rust
/// Model selection config. References a provider and a specific model.
pub struct ProviderWithModel {
    pub provider_id: String,
    pub model: String,
    pub use_model: Option<String>,
}
```

> 来源：模块 04（提供商管理）、05（会话创建/更新）、09（通道默认模型配置）。

### C.2 IConfirmation — 工具调用确认项

```rust
/// A pending tool-call confirmation item.
pub struct Confirmation {
    pub id: String,
    pub call_id: String,
    pub title: Option<String>,
    pub action: Option<String>,
    pub description: String,
    pub command_type: Option<String>,
    pub options: Vec<ConfirmationOption>,
}

pub struct ConfirmationOption {
    pub label: String,
    pub value: serde_json::Value,
    pub params: Option<HashMap<String, String>>,
}
```

> 来源：模块 05（确认系统 REST API + WebSocket 事件）、06（Agent 实现中的确认处理）、09（通道消息工具确认）。

### C.3 VersionInfo — 版本信息模型

```rust
/// Semantic version info with comparison and update detection.
pub struct VersionInfo {
    pub current: String,
    pub latest: String,
    pub minimum_required: Option<String>,
    pub release_notes: Option<String>,
}
```

> 来源：模块 14（更新检查）、13（扩展引擎兼容性校验）。提供 `is_update_available()`、`is_forced()`、`get_update_type()` 等方法。

---

## D. aionui-api-types — API DTO

HTTP/WebSocket 请求响应的专用类型。各模块的 REST API handler 和 WebSocket 事件处理使用这些 DTO 与客户端交互。

### D.1 统一 API 响应信封

```rust
/// Standard API success response.
pub struct ApiResponse<T: Serialize> {
    pub success: bool,  // always true
    pub data: Option<T>,
    pub message: Option<String>,
}

/// Standard API error response.
pub struct ErrorResponse {
    pub success: bool,  // always false
    pub error: String,
    pub code: String,
}
```

> **设计决策**：原实现中错误响应格式不一致（有的用 `message`，有的用 `error`，有的带 `details`）。Rust 重写时统一：成功用 `ApiResponse<T>`，错误用 `ErrorResponse`。`AppError` 自动转换为 `ErrorResponse`。

### D.2 WebSocket 消息格式

```rust
/// All WebSocket messages follow this format.
pub struct WebSocketMessage<T: Serialize> {
    pub name: String,
    pub data: T,
}
```

> 来源：模块 07（WebSocket 协议定义）。

### D.3 各模块 DTO

以下 DTO 类型按所属模块组织。它们定义在 `aionui-api-types` 中，但仅被对应模块使用。不逐一展开结构体定义（各模块文档中已有详细描述），仅列出归属索引：

| 模块 | 请求 DTO | 响应 DTO |
|------|---------|---------|
| 03 - 认证 | `LoginRequest`, `ChangePasswordRequest`, `QrLoginRequest` | `LoginResponse`, `AuthStatusResponse` |
| 04 - 系统设置 | `UpdateSettingsRequest`, `CreateProviderRequest`, `DetectProtocolRequest` | `ProviderResponse`, `ProtocolDetectionResponse` |
| 05 - 会话 | `CreateConversationRequest`, `SendMessageRequest`, `ConfirmRequest`, `CloneConversationRequest` | `ConversationResponse`, `MessageSearchResponse`, `SideQuestionResponse` |
| 06 - AI 后端 | `BedrockTestRequest`, `CreateRemoteAgentRequest` | `RemoteAgentResponse`, `McpConnectionTestResult` |
| 08 - 文件 | `CopyFilesRequest`, `DocumentConversionRequest` | `FileMetadataResponse`, `ConversionResponse` |
| 09 - 通道 | `EnablePluginRequest`, `ApprovePairingRequest` | `PluginStatusResponse`, `PairingRequestResponse` |
| 10 - 团队 | `CreateTeamRequest`, `SendTeamMessageRequest`, `AddAgentRequest` | `TeamResponse`, `TeamAgentResponse` |
| 11 - 定时任务 | `CreateCronJobRequest`, `SaveCronSkillRequest` | `CronJobResponse`, `CronJobExecutedEvent` |
| 12 - MCP | `SyncToAgentsRequest`, `TestMcpConnectionRequest`, `OAuthLoginRequest` | `McpSyncResult`, `DetectedMcpServerResponse` |
| 13 - 扩展 | `InstallExtensionRequest` | `ExtensionSummaryResponse`, `HubExtensionListResponse`, `PermissionSummaryResponse` |
| 14 - 生命周期 | `UpdateCheckRequest`, `UpdateDownloadRequest` | `UpdateCheckResult`, `SystemInfoResponse`, `WebUIStatusResponse`, `QRTokenResult` |
| 16 - Office 预览 | `StartPreviewRequest`, `SaveSnapshotRequest` | `PreviewUrlResponse`, `SnapshotListResponse` |
| 17 - Shell 与语音 | `SpeechToTextRequest` | `SpeechToTextResult` |

---

## E. 模块导出类型

以下类型定义在各自所属的模块 crate 中，但通过 `pub use` 导出供其他模块使用。

### E.1 aionui-db 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `User` | 用户模型（对应 users 表） | auth, conversation, app-lifecycle |
| `ConversationRow` | 会话持久化模型（对应 conversations 表） | conversation, channel, cron |
| `MessageRow` | 消息持久化模型（对应 messages 表） | conversation |
| `CronJobRow` | 定时任务持久化模型（对应 cron_jobs 表） | cron |
| `RemoteAgentRow` | 远程 Agent 持久化模型（对应 remote_agents 表） | ai-agent |
| `ChannelPluginRow` | 通道插件持久化模型（对应 assistant_plugins 表） | channel |

### E.2 aionui-system 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `IProvider` | 模型提供商配置 | conversation, ai-agent, channel, cron |
| `ModelCapability` / `ModelType` | 模型能力描述 | conversation, extension |
| `BedrockConfig` | AWS Bedrock 专属配置 | ai-agent |
| `SystemSettings` | 系统设置核心字段 | cron（通知开关）, app-lifecycle |

### E.3 aionui-ai-agent 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `RemoteAgentConfig` | 远程 Agent 完整配置 | conversation（创建远程会话） |
| `SkillDefinition` / `SkillIndex` | 技能定义 | extension（技能贡献解析）, cron（Skill 文件管理） |
| `AcpSessionMcpServer` | ACP session MCP 注入格式 | mcp（构建注入列表） |
| `AcpMcpCapabilities` | ACP 后端 MCP 能力声明 | mcp（过滤支持的 transport） |

### E.4 aionui-mcp 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `IMcpServer` | MCP 服务器配置 | extension（MCP 服务器贡献）, ai-agent（session 注入） |
| `IMcpServerTransport` | 传输方式枚举 | extension, ai-agent |
| `IMcpTool` | MCP 工具描述 | extension |
| `McpSource` | Agent 来源标识枚举 | extension, ai-agent |

### E.5 aionui-extension 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `ExtensionManifest` | 扩展清单 | extension（内部） |
| `ResolvedModelProvider` | 解析后的模型提供商 | system-settings（合并扩展提供商） |
| `ResolvedAssistant` | 解析后的助手定义 | conversation（助手选择） |
| `ResolvedAcpAdapter` | 解析后的 ACP 适配器 | ai-agent（扩展 ACP 后端） |
| `ExtMcpServer` | 扩展贡献的 MCP 服务器 | mcp（合并到配置列表） |

### E.6 aionui-channel 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `PluginType` | 平台标识枚举 | conversation（source 映射） |
| `IUnifiedIncomingMessage` | 统一入站消息 | channel（内部） |
| `IUnifiedOutgoingMessage` | 统一出站消息 | channel（内部） |

### E.7 aionui-team 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `TTeam` | 团队描述 | conversation（teamId 关联） |
| `TeamAgent` | 团队 Agent 描述 | conversation（团队会话） |
| `TeammateRole` / `TeammateStatus` | Agent 角色/状态枚举 | WebSocket 事件载荷 |

### E.8 aionui-cron 导出

| 类型 | 说明 | 消费方 |
|------|------|--------|
| `CronJob` | 定时任务完整描述 | conversation（关联查询） |
| `CronSchedule` | 调度类型枚举 | api-types（创建请求） |

---

## F. Trait 定义

### F.1 Repository Trait（aionui-db）

数据访问层的统一抽象。各业务模块通过 trait 访问数据，不直接依赖具体实现。

| Trait | 说明 | 实现方 |
|-------|------|--------|
| `IConversationRepository` | 会话 + 消息 CRUD、分页、搜索 | `SqliteConversationRepository` |
| `IChannelRepository` | 通道插件、用户、会话、配对码 | `SqliteChannelRepository` |
| `ITeamRepository` | 团队 + 邮箱 + 任务板 | `SqliteTeamRepository` |
| `ICronRepository` | 定时任务 CRUD | `SqliteCronRepository` |
| `IUserRepository` | 用户 CRUD、认证查询 | `SqliteUserRepository` |

> 详见模块 02（Repository 接口定义）和各模块的 Repository 接口节。

### F.2 Service Trait（各业务 crate）

业务逻辑层的抽象。`aionui-app` 负责依赖注入和组装。

| Trait | 所在 crate | 说明 |
|-------|-----------|------|
| `IConversationService` | `aionui-conversation` | 会话生命周期管理 |
| `IAgentManager` | `aionui-ai-agent` | 单个 Agent 实例接口（send_message, stop, confirm） |
| `IWorkerTaskManager` | `aionui-ai-agent` | Agent 任务池管理 |
| `McpAgentAdapter` | `aionui-mcp` | MCP 配置同步到各 CLI 的适配器 |
| `ChannelPlugin` | `aionui-channel` | 通道平台插件抽象 |
| `SpeechToTextProvider` | `aionui-shell` | STT Provider 抽象 |

### F.3 事件广播（aionui-realtime）

```rust
/// Broadcast an event to all connected WebSocket clients.
pub trait EventBroadcaster: Send + Sync {
    fn broadcast(&self, event: WebSocketMessage<serde_json::Value>);
}
```

所有需要推送 WebSocket 事件的模块通过此 trait 发布事件，不直接依赖 WebSocket 实现。

---

## G. 常量

跨模块共享的常量值。

### G.1 文件处理常量

| 常量 | 值 | 说明 | 来源模块 |
|------|-----|------|---------|
| `AIONUI_TIMESTAMP_SEPARATOR` | `"_aionui_"` | 文件名中的时间戳分隔符 | 04 |
| `AIONUI_FILES_MARKER` | `"[[AION_FILES]]"` | 消息中的文件占位标记 | 04 |

### G.2 WebSocket 常量

| 常量 | 值 | 说明 | 来源模块 |
|------|-----|------|---------|
| `HEARTBEAT_INTERVAL_MS` | `30000` | 心跳发送间隔 | 07 |
| `HEARTBEAT_TIMEOUT_MS` | `60000` | 心跳超时 | 07 |
| `WS_CLOSE_NORMAL` | `1000` | 正常关闭码 | 07 |
| `WS_CLOSE_POLICY_VIOLATION` | `1008` | 策略违规关闭码 | 07 |

### G.3 认证常量

| 常量 | 值 | 说明 | 来源模块 |
|------|-----|------|---------|
| `SESSION_EXPIRY` | `"24h"` | JWT 会话过期时间 | 03 |
| `COOKIE_NAME` | `"aionui-session"` | Session cookie 名称 | 03 |
| `COOKIE_MAX_AGE_DAYS` | `30` | Cookie 存活天数 | 03 |
| `CSRF_COOKIE_NAME` | `"aionui-csrf-token"` | CSRF token cookie 名称 | 14 |
| `CSRF_HEADER_NAME` | `"x-csrf-token"` | CSRF token 请求头 | 14 |

### G.4 服务器常量

| 常量 | 值 | 说明 | 来源模块 |
|------|-----|------|---------|
| `DEFAULT_PORT` | `25808` | 默认服务端口 | 14 |
| `BODY_LIMIT` | `10 MB` | 请求体大小限制 | 14 |
| `UPLOAD_MAX_SIZE` | `30 MB` | 文件上传大小限制 | 14 |

### G.5 图片处理常量

| 常量 | 值 | 说明 | 来源模块 |
|------|-----|------|---------|
| 支持的图片扩展名 | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.svg` | — | 04 |
| 远程图片大小上限 | `5 MB` | fetchRemoteImage | 08 |
| 远程图片重定向上限 | `5 次` | — | 08 |

---

## H. 类型归属决策树

当新增类型不确定归属时，按以下规则判断：

```
该类型被几个 crate 使用？
  │
  ├─ 1 个 → 留在该 crate 内部，不导出
  │
  ├─ 2+ 个 → 是否涉及 HTTP/WS 请求响应？
  │     │
  │     ├─ 是 → aionui-api-types
  │     │
  │     └─ 否 → 是否涉及数据库表映射？
  │           │
  │           ├─ 是 → aionui-db
  │           │
  │           └─ 否 → aionui-common
  │
  └─ 所有 crate → aionui-common（基础设施类型）
```

---

## I. 设计决策

### 1. 状态字段改用枚举

原实现中大量状态字段使用字符串字面量 + CHECK 约束。Rust 中统一定义为枚举类型（`#[derive(sqlx::Type)]` 或自定义序列化），获得编译时类型安全和穷尽匹配检查。

涉及的枚举：`ConversationStatus`、`MessageStatus`、`MessagePosition`、`RemoteAgentStatus`、`AgentType`、`AcpBackend`、`ConversationSource` 等。

### 2. JSON 字段处理

原实现中数据库大量使用 JSON 文本字段（`extra`、`content`、`agents`、`config` 等）。Rust 中通过 `serde_json::Value` 存储通用 JSON，按类型判别字段反序列化为具体结构体。

### 3. 废弃 IBridgeResponse

原实现中 `IBridgeResponse<D> { success, data?, msg? }` 用于 IPC 返回值。Rust 中 IPC 概念不存在，所有接口通过 REST API / WebSocket 通信，使用 `ApiResponse<T>` / `Result<T, AppError>` 替代。

### 4. Crate 间通信仅通过 trait

- 依赖方向严格向下，禁止循环依赖
- `aionui-app` 是唯一知道所有 crate 的地方，负责依赖注入和组装
- `aionui-common` 是最底层，零业务逻辑
- 业务 crate 之间通过 trait + `Arc<dyn Trait>` 通信

### 5. serde 序列化策略

所有对外 API 类型使用 `#[serde(rename_all = "camelCase")]`，与前端 JavaScript 命名风格一致。数据库模型使用 `snake_case`（与 SQL 列名一致）。两层之间的转换在 service 层完成。

---

## 模块依赖图

```
aionui-common          ← 所有 crate 依赖
    ↑
aionui-db              ← 所有业务 crate 依赖
    ↑
aionui-api-types       ← HTTP/WS 路由层依赖
    ↑
┌────┼────┬────┬────┬────┬────┬────┬────┬────┐
│auth│conv│agent│rt  │file│chan│team│cron│mcp │...
└────┴────┴────┴────┴────┴────┴────┴────┴────┘
                    ↑
              aionui-app (顶层组装)
```

> 此结构为初步设计。最终 crate 结构和依赖关系将在 `99-rust-crate-mapping.md` 中确定。
