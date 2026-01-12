# Requirements Document

## Introduction

本功能为 QQ 机器人实现群友人设画像系统。通过持续收集群友的聊天记录，利用 LLM 分析并构建每个群友的人设标签，使机器人能够像真实群友一样了解每个人的性格、兴趣和说话风格。

## Glossary

- **Profile_System**: 群友人设画像系统，负责收集消息、分析人设、存储和查询
- **Message_Buffer**: 消息缓冲模块，临时存储群友消息直到达到分析阈值
- **Profile_Analyzer**: 人设分析模块，调用 LLM 分析消息并生成/更新人设
- **Profile_Store**: 人设存储模块，使用 SQLite 持久化存储人设数据
- **User_Profile**: 单个群友的人设数据，包含昵称、性格、兴趣等信息

## Requirements

### Requirement 1: 消息收集与缓冲

**User Story:** 作为机器人，我需要收集每个群友的聊天消息并缓冲，以便积累足够数据进行人设分析。

#### Acceptance Criteria

1. WHEN 群友发送消息 THEN THE Message_Buffer SHALL 将消息存入 SQLite 数据库
2. WHEN 存储消息时 THEN THE Message_Buffer SHALL 记录 group_id、user_id、消息内容和时间戳
3. WHEN 某群友在某群的缓冲消息达到 10 条 THEN THE Profile_System SHALL 触发人设分析流程
4. WHEN 消息被用于分析后 THEN THE Message_Buffer SHALL 清空该用户的缓冲消息

### Requirement 2: 人设分析与生成

**User Story:** 作为机器人，我需要通过 LLM 分析群友的聊天记录来生成和更新人设描述。

#### Acceptance Criteria

1. WHEN 触发人设分析 THEN THE Profile_Analyzer SHALL 获取该用户的 10 条新消息和现有人设
2. WHEN 调用 LLM 分析时 THEN THE Profile_Analyzer SHALL 将新消息和现有人设一并发送给 LLM
3. WHEN LLM 返回分析结果 THEN THE Profile_Analyzer SHALL 从结果中提取昵称、性格、兴趣、说话风格等信息
4. IF 用户是首次分析（无现有人设）THEN THE Profile_Analyzer SHALL 让 LLM 从消息中推断昵称和基础人设
5. WHEN 分析完成 THEN THE Profile_Analyzer SHALL 更新用户的累计消息计数

### Requirement 3: 人设持久化存储

**User Story:** 作为机器人，我需要将群友人设持久化存储，以便重启后保留所有数据。

#### Acceptance Criteria

1. WHEN 系统启动时 THEN THE Profile_Store SHALL 自动创建 SQLite 数据库和表结构（如不存在）
2. WHEN 存储人设时 THEN THE Profile_Store SHALL 以 (group_id, user_id) 为主键存储
3. WHEN 更新人设时 THEN THE Profile_Store SHALL 保留历史消息计数并累加
4. WHEN 查询人设时 THEN THE Profile_Store SHALL 支持按 group_id 和 user_id 查询

### Requirement 4: 人设查询与应用

**User Story:** 作为机器人，我需要在回复时查询群友人设，以便生成更个性化的回复。

#### Acceptance Criteria

1. WHEN 机器人需要回复某用户时 THEN THE Profile_System SHALL 提供该用户的人设信息
2. WHEN 查询人设时 THEN THE Profile_System SHALL 返回人设描述文本（如存在）
3. IF 用户无人设记录 THEN THE Profile_System SHALL 返回空或默认提示
4. WHEN 生成回复时 THEN THE AI_Chat_Plugin SHALL 将人设信息注入到 system prompt 中

### Requirement 5: 数据库自动初始化

**User Story:** 作为开发者，我希望数据库表结构能自动创建，无需手动初始化。

#### Acceptance Criteria

1. WHEN 系统首次启动 THEN THE Profile_Store SHALL 自动创建 data/profiles.db 文件
2. WHEN 数据库文件不存在时 THEN THE Profile_Store SHALL 创建 message_buffer 表和 user_profile 表
3. WHEN 数据库已存在时 THEN THE Profile_Store SHALL 直接使用现有数据，不覆盖

### Requirement 6: LLM 智能提取信息

**User Story:** 作为机器人，我希望 LLM 能从聊天记录中智能提取用户信息，无需预填写任何字段。

#### Acceptance Criteria

1. WHEN 分析用户消息时 THEN THE Profile_Analyzer SHALL 让 LLM 推断用户可能的昵称/称呼
2. WHEN 分析用户消息时 THEN THE Profile_Analyzer SHALL 让 LLM 分析用户的性格特点
3. WHEN 分析用户消息时 THEN THE Profile_Analyzer SHALL 让 LLM 分析用户的兴趣爱好
4. WHEN 分析用户消息时 THEN THE Profile_Analyzer SHALL 让 LLM 分析用户的说话风格
5. WHEN 分析用户消息时 THEN THE Profile_Analyzer SHALL 让 LLM 猜测用户的职业/身份
6. WHEN 信息不足以判断某项时 THEN THE Profile_Analyzer SHALL 允许 LLM 标注"未知"或省略该项
