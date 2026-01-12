# Implementation Plan: User Profile System

## Overview

实现群友人设画像系统，包括 SQLite 数据库模块、人设分析模块，以及与现有 AI 聊天插件的集成。

## Tasks

- [x] 1. 创建 ProfileDatabase 数据库模块
  - [x] 1.1 创建 `plugins/profile_db.py` 文件，实现 ProfileDatabase 类
    - 实现 `__init__` 方法，自动创建数据库和表结构
    - 实现 `add_message` 方法，添加消息到缓冲区并返回当前计数
    - 实现 `get_buffer_messages` 方法，获取用户缓冲消息
    - 实现 `clear_buffer` 方法，清空用户缓冲消息
    - 实现 `get_profile` 方法，查询用户人设
    - 实现 `update_profile` 方法，更新或插入用户人设
    - _Requirements: 1.1, 1.2, 1.4, 3.1, 3.2, 3.3, 3.4, 5.1, 5.2, 5.3_

  - [ ]* 1.2 编写 ProfileDatabase 属性测试
    - **Property 1: 消息存储完整性**
    - **Property 2: 触发阈值准确性**
    - **Property 3: 缓冲清空正确性**
    - **Property 4: 人设更新累加性**
    - **Property 5: 主键唯一性**
    - **Property 6: 数据持久性**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.5, 3.2, 3.3, 5.3**

- [x] 2. 创建 ProfileAnalyzer 分析模块
  - [x] 2.1 创建 `plugins/profile_analyzer.py` 文件，实现 ProfileAnalyzer 类
    - 实现 `__init__` 方法，接收 ProfileDatabase 实例
    - 实现 `build_analysis_prompt` 方法，构建 LLM 分析 prompt
    - 实现 `parse_llm_response` 方法，解析 LLM 返回的昵称和人设
    - 实现 `analyze_and_update` 方法，完整的分析更新流程
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 2.2 编写 ProfileAnalyzer 单元测试
    - 测试 `build_analysis_prompt` 生成正确的 prompt 格式
    - 测试 `parse_llm_response` 正确解析各种 LLM 返回格式
    - _Requirements: 2.2, 2.3_

- [x] 3. 集成到 AI 聊天插件
  - [x] 3.1 修改 `plugins/ai_chat_plugin.py`，集成人设系统
    - 创建全局 ProfileDatabase 和 ProfileAnalyzer 实例
    - 在 `handle_group_watcher` 中添加消息收集逻辑
    - 当消息数达到 10 条时触发 `analyze_and_update`
    - _Requirements: 1.3, 2.1_

  - [x] 3.2 修改 AI 回复逻辑，注入人设信息
    - 在 `handle_ai_chat` 中查询用户人设
    - 将人设信息注入到 system prompt 中
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 3.3 编写人设注入属性测试
    - **Property 7: 人设注入正确性**
    - **Validates: Requirements 4.4**

- [x] 4. Checkpoint - 确保所有测试通过
  - 运行所有测试，确保功能正常
  - 如有问题请询问用户

## Notes

- 任务标记 `*` 为可选测试任务
- SQLite 使用 Python 内置 `sqlite3` 模块，无需额外依赖
- 数据库文件存放在 `data/profiles.db`
- 每个属性测试引用设计文档中的对应属性
