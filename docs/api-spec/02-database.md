# 02 - 数据模型与存储

## 概述

管理 SQLite 数据库的初始化、Schema 定义、数据迁移、以及所有业务数据的 CRUD 操作，是整个系统的数据持久化基础。

## 源码位置

`src/process/services/database/`

## 数据表定义

### users — 用户账户

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| username | TEXT | UNIQUE, NOT NULL | 用户名 |
| email | TEXT | UNIQUE | 邮箱 |
| password_hash | TEXT | NOT NULL | 密码哈希 |
| avatar_path | TEXT | | 头像路径 |
| jwt_secret | TEXT | | 用户独立的 JWT 密钥 |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| updated_at | INTEGER | NOT NULL | 更新时间戳 |
| last_login | INTEGER | | 最后登录时间戳 |

索引：`idx_users_username`, `idx_users_email`

### conversations — 会话

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| user_id | TEXT | FK → users.id | 所属用户 |
| name | TEXT | NOT NULL | 会话名称 |
| type | TEXT | NOT NULL | 会话类型（见下方枚举） |
| extra | TEXT | | JSON，类型特定的扩展数据 |
| model | TEXT | | JSON，TProviderWithModel |
| status | TEXT | CHECK: pending/running/finished | 会话状态 |
| source | TEXT | | 来源平台 |
| channel_chat_id | TEXT | | 通道聊天隔离 ID |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| updated_at | INTEGER | NOT NULL | 更新时间戳 |

**会话类型（type）**：gemini, acp, codex, openclaw-gateway, nanobot, remote, aionrs（v22 后移除 CHECK 约束，支持运行时扩展）

**来源（source）**：aionui, telegram, lark, dingtalk, weixin 及自定义字符串

索引：`idx_conversations_user_id`, `idx_conversations_updated_at`, `idx_conversations_type`, `idx_conversations_user_updated`, `idx_conversations_source`, `idx_conversations_source_updated`, `idx_conversations_source_chat`, `idx_conversations_cron_job_id`

### messages — 消息

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| conversation_id | TEXT | FK → conversations.id | 所属会话 |
| msg_id | TEXT | | 流式消息关联 ID（用于去重/合并） |
| type | TEXT | NOT NULL | 消息类型（见下方枚举） |
| content | TEXT | NOT NULL | JSON，类型特定的消息内容 |
| position | TEXT | CHECK: left/right/center/pop | 显示位置 |
| status | TEXT | CHECK: finish/pending/error/work | 消息状态 |
| hidden | INTEGER | DEFAULT 0 | 是否隐藏 |
| created_at | INTEGER | NOT NULL | 创建时间戳 |

**消息类型（type）**：text, tips, tool-call, tool-group, agent-status, acp-permission, acp-tool-call, codex-permission, codex-tool-call, plan, thinking, available-commands, skill-suggest, cron-trigger

索引：`idx_messages_conversation_id`, `idx_messages_created_at`, `idx_messages_type`, `idx_messages_msg_id`, `idx_messages_conversation_created`

### teams — 团队

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| user_id | TEXT | FK → users.id | 所属用户 |
| name | TEXT | NOT NULL | 团队名称 |
| workspace | TEXT | | 工作区路径 |
| workspace_mode | TEXT | | 工作区模式 |
| lead_agent_id | TEXT | | 主导 Agent ID |
| agents | TEXT | | JSON 数组，成员 Agent 列表 |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| updated_at | INTEGER | NOT NULL | 更新时间戳 |

索引：`idx_teams_user_id`, `idx_teams_updated_at`

### mailbox — 团队邮箱（Agent 间消息）

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| team_id | TEXT | FK → teams.id | 所属团队 |
| to_agent_id | TEXT | NOT NULL | 接收 Agent |
| from_agent_id | TEXT | NOT NULL | 发送 Agent |
| type | TEXT | DEFAULT 'message' | 消息类型 |
| content | TEXT | NOT NULL | 消息内容 |
| summary | TEXT | | 摘要 |
| read | INTEGER | DEFAULT 0 | 是否已读 |
| created_at | INTEGER | NOT NULL | 创建时间戳 |

索引：`idx_mailbox_to`

### team_tasks — 团队任务

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| team_id | TEXT | FK → teams.id | 所属团队 |
| subject | TEXT | NOT NULL | 任务标题 |
| description | TEXT | | 任务描述 |
| status | TEXT | DEFAULT 'pending' | pending/in_progress/completed |
| owner | TEXT | | 负责 Agent |
| blocked_by | TEXT | | JSON，阻塞依赖 |
| blocks | TEXT | | JSON，被阻塞任务 |
| metadata | TEXT | | JSON，扩展数据 |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| updated_at | INTEGER | NOT NULL | 更新时间戳 |

索引：`idx_tasks_team`

### assistant_plugins — 通道插件

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| type | TEXT | NOT NULL | 插件类型（telegram/lark/dingtalk/weixin 等） |
| name | TEXT | NOT NULL | 插件名称 |
| enabled | INTEGER | DEFAULT 0 | 是否启用 |
| config | TEXT | | JSON: {credentials, config}，凭证加密存储 |
| status | TEXT | | 连接状态 |
| last_connected | INTEGER | | 最后连接时间 |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| updated_at | INTEGER | NOT NULL | 更新时间戳 |

索引：`idx_assistant_plugins_type`, `idx_assistant_plugins_enabled`

### assistant_users — 通道授权用户

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| platform_user_id | TEXT | NOT NULL | 平台用户 ID |
| platform_type | TEXT | NOT NULL | 平台类型 |
| display_name | TEXT | | 显示名称 |
| authorized_at | INTEGER | NOT NULL | 授权时间 |
| last_active | INTEGER | | 最后活跃时间 |
| session_id | TEXT | | 关联会话 ID |

索引：`idx_assistant_users_platform`

### assistant_sessions — 通道用户会话

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| user_id | TEXT | FK → assistant_users.id | 关联用户 |
| agent_type | TEXT | CHECK: gemini/acp/codex | Agent 类型 |
| conversation_id | TEXT | FK → conversations.id | 关联会话 |
| workspace | TEXT | | 工作区 |
| chat_id | TEXT | | 通道聊天 ID（user:xxx, group:xxx） |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| last_activity | INTEGER | NOT NULL | 最后活跃时间 |

索引：`idx_assistant_sessions_user`, `idx_assistant_sessions_conversation`

### assistant_pairing_codes — 配对请求

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| code | TEXT | PK | 配对码 |
| platform_user_id | TEXT | NOT NULL | 平台用户 ID |
| platform_type | TEXT | NOT NULL | 平台类型 |
| display_name | TEXT | | 显示名称 |
| requested_at | INTEGER | NOT NULL | 请求时间 |
| expires_at | INTEGER | NOT NULL | 过期时间 |
| status | TEXT | CHECK: pending/approved/rejected/expired | 配对状态 |

索引：`idx_assistant_pairing_expires`, `idx_assistant_pairing_status`

### cron_jobs — 定时任务

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| name | TEXT | NOT NULL | 任务名称 |
| enabled | INTEGER | DEFAULT 1 | 是否启用 |
| schedule_kind | TEXT | NOT NULL | at/every/cron |
| schedule_value | TEXT | NOT NULL | 调度值 |
| schedule_tz | TEXT | | 时区 |
| schedule_description | TEXT | | 调度描述 |
| payload_message | TEXT | NOT NULL | 执行消息内容 |
| conversation_id | TEXT | FK → conversations.id | 关联会话 |
| conversation_title | TEXT | | 会话标题 |
| agent_type | TEXT | | Agent 类型 |
| created_by | TEXT | DEFAULT 'user' | user/agent |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| updated_at | INTEGER | NOT NULL | 更新时间戳 |
| next_run_at | INTEGER | | 下次执行时间 |
| last_run_at | INTEGER | | 上次执行时间 |
| last_status | TEXT | | 上次执行状态 |
| last_error | TEXT | | 上次错误信息 |
| run_count | INTEGER | DEFAULT 0 | 累计执行次数 |
| retry_count | INTEGER | DEFAULT 0 | 当前重试次数 |
| max_retries | INTEGER | DEFAULT 3 | 最大重试次数 |
| execution_mode | TEXT | DEFAULT 'existing' | existing/new_conversation |
| agent_config | TEXT | | JSON，Agent 配置 |

索引：`idx_cron_jobs_conversation`, `idx_cron_jobs_next_run`, `idx_cron_jobs_agent_type`

### remote_agents — 远程 Agent

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | TEXT | PK | UUID |
| name | TEXT | NOT NULL | Agent 名称 |
| protocol | TEXT | DEFAULT 'openclaw' | 协议类型 |
| url | TEXT | NOT NULL | 连接地址 |
| auth_type | TEXT | | 认证类型 |
| auth_token | TEXT | | 认证令牌（加密存储） |
| avatar | TEXT | | 头像 |
| description | TEXT | | 描述 |
| status | TEXT | | 连接状态 |
| last_connected_at | INTEGER | | 最后连接时间 |
| device_id | TEXT | | 设备 ID |
| device_public_key | TEXT | | 设备公钥（加密存储） |
| device_private_key | TEXT | | 设备私钥（加密存储） |
| device_token | TEXT | | 设备令牌（加密存储） |
| allow_insecure | INTEGER | DEFAULT 0 | 允许不安全连接 |
| created_at | INTEGER | NOT NULL | 创建时间戳 |
| updated_at | INTEGER | NOT NULL | 更新时间戳 |

索引：`idx_remote_agents_protocol`

## 数据库配置

| 配置项 | 值 | 说明 |
|--------|---|------|
| foreign_keys | ON | 启用外键约束 |
| busy_timeout | 5000ms | 繁忙超时 |
| journal_mode | WAL | Write-Ahead Logging，支持并发读写 |
| 当前版本 | 22 | 22 次迁移 |

## Repository 接口

### IConversationRepository

会话与消息的数据访问接口。

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getConversation | id: string | TChatConversation \| undefined | 根据 ID 获取会话 |
| createConversation | conversation: TChatConversation | void | 创建会话 |
| updateConversation | id: string, updates: Partial\<TChatConversation\> | void | 部分更新会话 |
| deleteConversation | id: string | void | 删除会话及其所有消息 |
| getMessages | id: string, page: number, pageSize: number, order?: ASC\|DESC | PaginatedResult\<TMessage\> | 分页获取会话消息 |
| insertMessage | message: TMessage | void | 插入消息 |
| getUserConversations | cursor?: string, offset?: number, limit?: number | PaginatedResult\<TChatConversation\> | 分页获取用户会话列表 |
| listAllConversations | — | TChatConversation[] | 获取所有会话（无分页） |
| searchMessages | keyword: string, page: number, pageSize: number | IMessageSearchResponse | 跨会话搜索消息内容 |
| getConversationsByCronJob | cronJobId: string | TChatConversation[] | 获取关联定时任务的会话 |

### IChannelRepository

通道集成的数据访问接口。

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getChannelPlugins | — | IChannelPluginConfig[] | 获取所有通道插件配置 |
| getPendingPairingRequests | — | IChannelPairingRequest[] | 获取待处理的配对请求 |
| getChannelUsers | — | IChannelUser[] | 获取所有授权用户 |
| deleteChannelUser | userId: string | void | 删除授权用户 |
| getChannelSessions | — | IChannelSession[] | 获取所有通道会话 |

## 数据库主类操作

### 用户操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| createUser | username, passwordHash, email? | IQueryResult\<IUser\> | 创建用户 |
| getUser | id | IQueryResult\<IUser\> | 根据 ID 获取用户 |
| getUserByUsername | username | IQueryResult\<IUser\> | 根据用户名获取用户 |
| getAllUsers | — | IQueryResult\<IUser[]\> | 获取所有用户 |
| getUserCount | — | number | 获取用户总数 |
| hasUsers | — | boolean | 是否存在用户 |
| updateUserLastLogin | id | void | 更新最后登录时间 |
| updateUserPassword | id, passwordHash | void | 更新密码 |
| updateUserJwtSecret | id, jwtSecret | void | 更新 JWT 密钥 |
| setSystemUserCredentials | username, passwordHash | void | 设置系统用户凭证 |
| updateUserUsername | id, username | void | 更新用户名 |

### 会话操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| createConversation | conversation, userId | void | 创建会话（JSON 序列化 extra/model） |
| getConversation | id | TChatConversation \| undefined | 获取会话（JSON 反序列化） |
| findChannelConversation | source, chatId, type, backend | TChatConversation \| undefined | 按来源+聊天ID+类型+后端查找通道会话 |
| updateChannelConversationModel | id, model | void | 更新通道会话的模型配置 |
| getUserConversations | cursor?, offset?, limit? | PaginatedResult\<TChatConversation\> | 分页获取用户会话 |
| updateConversation | id, updates | void | 部分更新会话 |
| deleteConversation | id | void | 删除会话（级联删除消息） |
| getConversationsByCronJobId | cronJobId | TChatConversation[] | 获取定时任务关联的会话 |

### 消息操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| insertMessage | message | void | 插入消息（JSON 序列化 content） |
| getConversationMessages | id, page, pageSize, order? | PaginatedResult\<TMessage\> | 分页获取消息 |
| searchConversationMessages | keyword, page, pageSize | IMessageSearchResponse | 跨会话搜索消息（返回会话+预览） |
| updateMessage | id, updates | void | 更新消息内容/状态 |
| deleteMessage | id | void | 删除单条消息 |
| deleteConversationMessages | conversationId | void | 删除会话所有消息 |
| getMessageByMsgId | msgId | TMessage \| undefined | 根据 msg_id 获取消息（流式关联） |

### 通道插件操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getChannelPlugins | — | IChannelPluginConfig[] | 获取所有插件（凭证解密） |
| getChannelPlugin | id | IChannelPluginConfig \| undefined | 获取单个插件 |
| upsertChannelPlugin | config | void | 创建或更新插件（凭证加密） |
| updateChannelPluginStatus | id, status, lastConnected? | void | 更新插件连接状态 |
| deleteChannelPlugin | id | void | 删除插件 |

### 通道用户操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getChannelUsers | — | IChannelUser[] | 获取所有授权用户 |
| getChannelUserByPlatform | platformUserId, platformType | IChannelUser \| undefined | 按平台查找用户 |
| createChannelUser | user | IChannelUser | 创建授权用户 |
| updateChannelUserActivity | id | void | 更新用户活跃时间 |
| deleteChannelUser | id | void | 删除用户 |

### 通道会话操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getChannelSessions | — | IChannelSession[] | 获取所有会话 |
| getChannelSessionByUser | userId | IChannelSession \| undefined | 按用户获取会话 |
| upsertChannelSession | session | void | 创建或更新会话 |
| deleteChannelSession | id | void | 删除会话 |

### 配对码操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getPendingPairingRequests | — | IChannelPairingRequest[] | 获取待处理配对请求 |
| getPairingRequestByCode | code | IChannelPairingRequest \| undefined | 根据配对码查询 |
| createPairingRequest | request | void | 创建配对请求 |
| updatePairingRequestStatus | code, status | void | 更新配对状态 |
| cleanupExpiredPairingRequests | — | void | 清理过期配对请求 |

### 远程 Agent 操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getRemoteAgents | — | RemoteAgent[] | 获取所有远程 Agent（敏感字段解密） |
| getRemoteAgent | id | RemoteAgent \| undefined | 获取单个 Agent |
| createRemoteAgent | agent | RemoteAgent | 创建远程 Agent（敏感字段加密） |
| updateRemoteAgent | id, updates | RemoteAgent | 更新远程 Agent |
| deleteRemoteAgent | id | void | 删除远程 Agent |

### 管理操作

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| vacuum | — | void | 回收数据库空间 |

## 流式消息缓冲（StreamingMessageBuffer）

优化流式消息场景下的数据库写入性能。

### 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| UPDATE_INTERVAL | 300ms | 最大刷新间隔 |
| CHUNK_BATCH_SIZE | 20 | 触发刷新的块数 |

### 接口

| 方法 | 参数 | 功能语义 |
|------|------|---------|
| append | id, messageId, conversationId, chunk, mode | 追加流式块 |

**mode 参数**：
- `accumulate`：拼接块内容（用于增量流式）
- `replace`：替换为最新块（用于全量更新）

**刷新触发条件**（满足任一）：
- 块计数达到 CHUNK_BATCH_SIZE 的倍数
- 距上次数据库更新超过 UPDATE_INTERVAL

**性能收益**：将约 1000 次 UPDATE 降至约 10 次，100 倍性能提升。

## 数据库驱动

### ISqliteDriver 接口

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| prepare | sql: string | IStatement | 预编译 SQL |
| exec | sql: string | void | 执行 SQL |
| pragma | sql: string, options? | unknown | 执行 PRAGMA |
| transaction | fn: Function | Function | 事务包装 |
| close | — | void | 关闭连接 |

### 驱动实现

| 驱动 | 运行时 | 底层库 |
|------|--------|--------|
| BetterSqlite3Driver | Node.js | better-sqlite3 |
| BunSqliteDriver | Bun | bun:sqlite |

运行时自动检测，通过 `createDriver(dbPath)` 工厂方法创建。

> **Rust 重写说明**：Rust 版本不需要多驱动，直接使用 rusqlite 或 sqlx 即可。

## 迁移系统

### 迁移管理接口

| 方法 | 参数 | 返回值 | 功能语义 |
|------|------|--------|---------|
| getMigrationsToRun | fromVersion, toVersion | IMigration[] | 获取需执行的迁移列表 |
| getMigrationsToRollback | fromVersion, toVersion | IMigration[] | 获取需回滚的迁移列表 |
| runMigrations | db, fromVersion, toVersion | void | 事务性执行迁移 |
| rollbackMigrations | db, fromVersion, toVersion | void | 事务性回滚迁移 |
| getMigrationHistory | db | Array\<{version, name, timestamp}\> | 获取迁移历史 |
| isMigrationApplied | db, version | boolean | 检查迁移是否已应用 |

### 迁移特性

- 事务性执行，失败自动回滚
- 迁移前暂时禁用外键约束（表重建场景）
- 迁移后验证外键完整性
- 支持正向迁移和回滚

## 初始化与恢复

### 初始化流程

1. 创建驱动（自动检测运行时）
2. `initSchema()` — 创建表（如不存在）
3. 检查版本，若 currentVersion < 22 则执行迁移
4. 确保系统默认用户存在

### 损坏恢复

当初始化失败且判定为数据库损坏时：
1. 备份损坏文件到 `{dbPath}.backup.{timestamp}`
2. 删除 WAL 文件（-wal, -shm）
3. 使用全新数据库重试

## 核心数据类型

### TChatConversation

判别联合类型，按 `type` 字段区分 7 种会话类型（gemini, acp, codex, openclaw-gateway, nanobot, remote, aionrs），每种类型有独立的 `extra` 字段结构。

公共字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | UUID |
| name | string | 会话名称 |
| desc | string? | 描述 |
| type | ConversationType | 会话类型 |
| extra | TypeSpecificExtra | 类型特定扩展数据 |
| model | TProviderWithModel | 模型配置 |
| status | 'pending' \| 'running' \| 'finished' | 状态 |
| source | ConversationSource | 来源平台 |
| channelChatId | string? | 通道聊天 ID |
| createTime | number | 创建时间戳 |
| modifyTime | number | 修改时间戳 |

### TMessage

判别联合类型，按 `type` 字段区分 14 种消息类型。

公共字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | UUID |
| msg_id | string? | 流式消息关联 ID |
| conversation_id | string | 所属会话 ID |
| type | TMessageType | 消息类型 |
| content | TypeSpecificContent | 类型特定内容（JSON） |
| position | 'left' \| 'right' \| 'center' \| 'pop' | 显示位置 |
| status | 'finish' \| 'pending' \| 'error' \| 'work' | 消息状态 |
| hidden | boolean | 是否隐藏 |
| createdAt | number | 创建时间戳 |

### IQueryResult\<T\>

统一查询结果包装：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| data | T? | 数据 |
| error | string? | 错误信息 |

### IPaginatedResult\<T\> / PaginatedResult\<T\>

分页查询结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| data | T[] | 数据列表 |
| total | number | 总数 |
| page | number | 当前页 |
| pageSize | number | 每页大小 |
| hasMore | boolean | 是否有更多 |

### IMessageSearchResponse

消息搜索响应：

| 字段 | 类型 | 说明 |
|------|------|------|
| items | IMessageSearchItem[] | 搜索结果列表 |
| total | number | 总数 |
| page | number | 当前页 |
| pageSize | number | 每页大小 |
| hasMore | boolean | 是否有更多 |

IMessageSearchItem 包含 `conversation`（完整会话对象）、`messageId`、`messageType`、`messageCreatedAt`、`previewText`。

## 安全相关

### 加密存储

以下字段使用 `encryptString/decryptString` 工具方法加密：
- `assistant_plugins.config.credentials` — 通道插件凭证
- `remote_agents.auth_token` — 认证令牌
- `remote_agents.device_public_key` — 设备公钥
- `remote_agents.device_private_key` — 设备私钥
- `remote_agents.device_token` — 设备令牌

### 数据库行 ↔ 业务对象转换

| 函数 | 方向 | 说明 |
|------|------|------|
| conversationToRow | 业务 → 数据库 | JSON.stringify(extra, model) |
| rowToConversation | 数据库 → 业务 | JSON.parse(extra, model) |
| messageToRow | 业务 → 数据库 | JSON.stringify(content) |
| rowToMessage | 数据库 → 业务 | JSON.parse(content) |

## 模块依赖

### 依赖谁

- 无外部模块依赖（最底层）

### 被谁依赖

- 认证与用户管理（03）— 用户 CRUD
- 系统设置（04）— 配置读写
- 会话与消息管理（05）— 会话/消息 CRUD
- AI 后端集成（06）— 会话/消息读写
- 实时通信（07）— 流式消息缓冲
- 文件与工作区（08）— 数据持久化
- 通道集成（09）— 插件/用户/会话/配对管理
- 团队模式（10）— 团队/邮箱/任务管理
- 定时任务（11）— 定时任务 CRUD
- MCP 协议（12）— 配置读写
- 应用生命周期（14）— 数据库初始化与关闭

## 候选公共类型

以下类型在多个模块间共享，是 `aionui-common` crate 的候选：

- `IQueryResult<T>` — 通用查询结果包装
- `IPaginatedResult<T>` / `PaginatedResult<T>` — 分页结果
- `ConversationSource` — 会话来源枚举
- `TChatConversation` — 会话类型（或至少其公共字段子集）
- `TMessage` / `TMessageType` — 消息类型
- `IUser` — 用户数据结构

## Rust 重写注意事项

1. **驱动选择**：无需多驱动模式，直接使用 rusqlite（同步）或 sqlx-sqlite（异步）
2. **流式缓冲**：StreamingMessageBuffer 的批量写入优化需保留，可用 tokio 定时器实现
3. **类型灵活性**：v22 移除了 CHECK 约束，Rust 层需用 String 而非枚举表示可扩展字段
4. **加密**：需实现等效的 encryptString/decryptString，建议使用 ring 或 aes-gcm crate
5. **JSON 序列化**：extra/model/content 等 JSON 字段可用 serde_json::Value 或强类型反序列化
6. **迁移系统**：可用 refinery 或 sqlx::migrate! 管理数据库迁移
7. **单例管理**：Rust 中可用 `once_cell::sync::OnceCell` 或 `tokio::sync::OnceCell` 管理数据库实例
8. **损坏恢复**：需保留自动备份+重建机制
9. **WAL 模式**：rusqlite 原生支持 WAL 模式
10. **Per-Chat 隔离**：source + channel_chat_id + type 的复合查询需保留
