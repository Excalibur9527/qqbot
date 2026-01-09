import websocket
import json
import threading
import time
import random

# --- 配置区 ---
# 因为代码是和 docker 在同一台机器跑，直接连本地 IP 即可
# 注意：如果你之前改了 NapCat 的 ws 端口，这里也要改
WS_URL = "ws://127.0.0.1:3001"

# 机器人QQ号（用于检测@消息）
BOT_QQ = "123456789"  # 请替换为你的机器人QQ号

def get_length_reply(length):
    """根据长度生成回复内容"""
    if length < -20:
        replies = [
            f"今天你的长度是{length}cm，是小小男娘喔~",
            f"哎呀{length}cm，这也太小了，小男娘要加油啊！",
            f"{length}cm的长度，今天是平胸小男娘模式吗？",
            f"今天只有{length}cm，小小的一只，男娘属性MAX！"
        ]
    elif length < -10:
        replies = [
            f"今天你的长度是{length}cm，是小男娘喔~",
            f"{length}cm，不错的小男娘身材呢！",
            f"今天是{length}cm，小男娘模式启动！",
            f"{length}cm的长度，很可爱的男娘尺寸~"
        ]
    elif length < 0:
        replies = [
            f"今天你的长度是{length}cm，是伪娘喔~",
            f"{length}cm，今天是伪娘模式吗？",
            f"哎呀{length}cm，是可爱的伪娘呢！",
            f"{length}cm的长度，伪娘属性有点强~"
        ]
    elif length == 0:
        replies = [
            "今天你的长度是0cm，完全平了呢！",
            "0cm，今天是平板模式吗？",
            "今天完全是0cm，平板伪娘！",
            "0cm的长度，今天是纯平板呢~"
        ]
    elif length <= 10:
        replies = [
            f"今天你的长度是{length}cm，小小的一根呢~",
            f"{length}cm，今天是迷你尺寸吗？",
            f"哎呀{length}cm，小巧可爱呢！",
            f"{length}cm的长度，很可爱的小尺寸~"
        ]
    elif length <= 20:
        replies = [
            f"今天你的长度是{length}cm，标准尺寸呢~",
            f"{length}cm，今天是普通模式吗？",
            f"不错哦{length}cm，很标准的长度！",
            f"{length}cm的长度，正好合适呢~"
        ]
    else:
        replies = [
            f"今天你的长度是{length}cm，好长..",
            f"哇{length}cm，这么长的大宝贝！",
            f"{length}cm，今天是大长腿模式吗？",
            f"好家伙{length}cm，长得吓人啊！"
        ]

    return random.choice(replies)

def on_message(ws, message):
    # 1. 收到消息，将其转为 JSON 对象
    data = json.loads(message)

    # 为了防止日志刷屏，我们只把这类消息打印出来看看
    if 'post_type' in data and data['post_type'] != 'meta_event':
        print(f"[收到数据] {data}")

    # 2. 判断是否是"群消息"
    if data.get('post_type') == 'message' and data.get('message_type') == 'group':
        group_id = data['group_id'] # 哪个群
        user_id = data['user_id']   # 谁发的
        msg = data['raw_message']   # 发了什么

        # --- 3. 业务逻辑：牛子bot ---
        # 检查是否@机器人或者包含"今日长度"关键词
        is_at_bot = f"[CQ:at,qq={BOT_QQ}]" in msg
        is_length_command = "今日长度" in msg

        if is_at_bot or is_length_command:
            # 生成-30到30之间的随机长度
            length = random.randint(-30, 30)
            reply_text = get_length_reply(length)

            reply_content = {
                "action": "send_group_msg",
                "params": {
                    "group_id": group_id,
                    "message": f"[CQ:at,qq={user_id}] {reply_text}"
                }
            }
            # 发送回复
            ws.send(json.dumps(reply_content))
            print(f"[发送回复] 在群 {group_id} 回复了用户 {user_id}: {reply_text}")

        # --- 原有的测试功能 ---
        elif msg == "测试":
            reply_content = {
                "action": "send_group_msg",
                "params": {
                    "group_id": group_id,
                    "message": f"[CQ:at,qq={user_id}] 这里的风景不错，我在！"
                }
            }
            # 发送回复
            ws.send(json.dumps(reply_content))
            print(f"[发送回复] 在群 {group_id} 回复了用户 {user_id}")

def on_error(ws, error):
    print(f"发生错误: {error}")

def on_close(ws, close_status_code, close_msg):
    print("连接断开")

def on_open(ws):
    print("大脑已连接到 NapCat (身体)！等待消息中...")

if __name__ == "__main__":
    # 长连接，断开自动重连
    while True:
        ws = websocket.WebSocketApp(WS_URL,
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.run_forever()
        print("尝试重连中...")
        time.sleep(3)
