# Design Document: User Profile System

## Overview

群友人设画像系统通过持续收集群聊消息，利用 LLM 增量分析构建每个群友的人设标签。系统使用 SQLite 持久化存储，每收集 10 条消息触发一次 LLM 分析，将新消息与现有人设合并生成更完善的用户画像。

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     NoneBot2 Plugin                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Group Message │───▶│Message Buffer│───▶│   Profile    │  │
│  │   Handler    │    │   (SQLite)   │    │   Analyzer   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                              │                   │          │
│                              ▼                   ▼          │
│                      ┌──────────────┐    ┌──────────────┐  │
│                      │Profile Store │◀───│   LLM API    │  │
│                      │  (SQLite)    │    │              │  │
│                      └──────────────┘    └──────────────┘  │
│                              │                              │
│                              ▼                              │
│                      ┌──────────────┐                      │
│                      │  AI Chat     │                      │
│                      │  (注入人设)   │                      │
│                      └──────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. ProfileDatabase 类

负责 SQLite 数据库操作，包括消息缓冲和人设存储。

```python
class ProfileDatabase:
    def __init__(self, db_path: str = "data/profiles.db"):
        """初始化数据库连接，自动创建表结构"""
        pass
    
    def add_message(self, group_id: str, user_id: str, content: str) -> int:
        """添加消息到缓冲区，返回该用户当前缓冲消息数"""
        pass
    
    def get_buffer_messages(self, group_id: str, user_id: str) -> List[Dict]:
        """获取用户的缓冲消息列表"""
        pass
    
    def clear_buffer(self, group_id: str, user_id: str) -> None:
        """清空用户的缓冲消息"""
        pass
    
    def get_profile(self, group_id: str, user_id: str) -> Optional[Dict]:
        """获取用户人设，不存在返回 None"""
        pass
    
    def update_profile(self, group_id: str, user_id: str, 
                       nickname: str, profile: str, 
                       message_count_delta: int) -> None:
        """更新或插入用户人设，累加消息计数"""
        pass
```

### 2. ProfileAnalyzer 类

负责调用 LLM 分析消息并生成人设。

```python
class ProfileAnalyzer:
    def __init__(self, db: ProfileDatabase):
        """初始化分析器"""
        pass
    
    async def analyze_and_update(self, group_id: str, user_id: str) -> Optional[str]:
        """
        分析用户消息并更新人设
        1. 获取缓冲消息和现有人设
        2. 调用 LLM 分析
        3. 更新数据库
        4. 清空缓冲
        返回新的人设描述
        """
        pass
    
    def build_analysis_prompt(self, messages: List[Dict], 
                               old_profile: Optional[str]) -> str:
        """构建 LLM 分析 prompt"""
        pass
    
    def parse_llm_response(self, response: str) -> Dict:
        """解析 LLM 返回的人设信息"""
        pass
```

### 3. 集成到现有插件

修改 `ai_chat_plugin.py`，在消息处理流程中集成人设系统。

```python
# 全局实例
profile_db = ProfileDatabase()
profile_analyzer = ProfileAnalyzer(profile_db)

# 在 group_watcher 中添加消息收集
async def handle_group_watcher(bot: Bot, event: Event):
    # ... 现有逻辑 ...
    
    # 添加消息到人设系统
    count = profile_db.add_message(group_id, user_id, text_content)
    if count >= 10:
        await profile_analyzer.analyze_and_update(group_id, user_id)

# 在 AI 回复时注入人设
async def handle_ai_chat(bot: Bot, event: Event):
    # ... 获取用户人设 ...
    profile = profile_db.get_profile(group_id, user_id)
    
    # 注入到 system prompt
    if profile:
        system_prompt += f"\n\n【对方信息】{profile['profile']}"
```

## Data Models

### SQLite 表结构

```sql
-- 消息缓冲表
CREATE TABLE IF NOT EXISTS message_buffer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引加速查询
CREATE INDEX IF NOT EXISTS idx_buffer_group_user 
ON message_buffer(group_id, user_id);

-- 用户人设表
CREATE TABLE IF NOT EXISTS user_profile (
    group_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    nickname TEXT,           -- LLM推断的昵称
    profile TEXT,            -- 人设描述
    message_count INTEGER DEFAULT 0,  -- 累计分析的消息数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, user_id)
);
```

### 人设数据结构

```python
{
    "group_id": "123456",
    "user_id": "789012",
    "nickname": "小明",  # LLM从聊天中推断
    "profile": "一个喜欢玩游戏的程序员，说话比较直接，经常吐槽工作...",
    "message_count": 30,  # 已分析30条消息
    "updated_at": "2026-01-08 15:30:00"
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 消息存储完整性

*For any* 群消息，存入数据库后查询应包含 group_id、user_id、content 和 timestamp 四个字段，且值与输入一致。

**Validates: Requirements 1.1, 1.2**

### Property 2: 触发阈值准确性

*For any* 用户，当且仅当其缓冲消息数达到 10 条时，`add_message` 返回值应等于 10，触发分析条件成立。

**Validates: Requirements 1.3**

### Property 3: 缓冲清空正确性

*For any* 用户，调用 `clear_buffer` 后，`get_buffer_messages` 应返回空列表。

**Validates: Requirements 1.4**

### Property 4: 人设更新累加性

*For any* 用户，多次调用 `update_profile` 后，`message_count` 应等于所有 `message_count_delta` 的累加和。

**Validates: Requirements 2.5, 3.3**

### Property 5: 主键唯一性

*For any* (group_id, user_id) 组合，数据库中最多存在一条人设记录。

**Validates: Requirements 3.2**

### Property 6: 数据持久性

*For any* 已存储的人设数据，重新创建 ProfileDatabase 实例后，查询应返回相同数据。

**Validates: Requirements 5.3**

### Property 7: 人设注入正确性

*For any* 存在人设的用户，生成的 system prompt 应包含该用户的人设描述文本。

**Validates: Requirements 4.4**

## Error Handling

| 场景 | 处理方式 |
|------|----------|
| SQLite 写入失败 | 记录日志，不影响消息处理流程 |
| LLM API 调用失败 | 保留缓冲消息，下次继续尝试 |
| LLM 返回格式异常 | 使用原始返回作为人设描述 |
| 数据库文件损坏 | 自动重建空数据库 |

## Testing Strategy

### 单元测试

- 测试 `ProfileDatabase` 的 CRUD 操作
- 测试 `ProfileAnalyzer.build_analysis_prompt` 的 prompt 构建
- 测试 `ProfileAnalyzer.parse_llm_response` 的解析逻辑

### 属性测试

使用 `pytest` + `hypothesis` 进行属性测试：

- Property 1-6 通过生成随机 group_id、user_id、content 验证
- 每个属性测试运行 100 次以上

### 集成测试

- 模拟完整的消息收集 → 分析 → 存储流程
- 验证人设注入到 AI 回复的 prompt 中

## LLM Prompt 设计

### 人设分析 Prompt

```
你是用户画像分析师。根据群聊记录分析用户特征。

【现有人设】
{old_profile or "暂无，这是首次分析"}

【新增聊天记录】
{messages}

【分析要求】
1. 推断用户可能的昵称/称呼（从聊天中提取，如"我是小明"、被人叫"老王"等）
2. 分析性格特点（如：话多/话少、乐观/悲观、直接/委婉）
3. 分析兴趣爱好（如：游戏、动漫、编程、运动）
4. 分析说话风格（如：爱用表情、说话带梗、正经严肃）
5. 猜测职业/身份（如：学生、程序员、上班族）
6. 如果信息不足，可以标注"未知"或省略

【输出格式】
昵称: xxx（如无法判断写"未知"）
人设: 一段100字以内的人设描述，自然语言，不要列表
```
