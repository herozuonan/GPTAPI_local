from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import uuid
from flask_cors import CORS
import requests
import json
app = Flask(__name__)
CORS(app)
history = []  ##初始历史信息为空
# 储存会话历史和最后活动时间的字典
sessions = {}
MAX_HISTORY_LENGTH = 20  ##最大历史信息长度
api_key = 'sk-XXXX'  #默认OPENAIKEY
modelName = 'gpt-3.5-turbo'
url = "https://api.openai.com/v1/chat/completions"

##处理聊天消息和调用聊天模型
def cleanup_sessions():
    # 获取24小时前的时间
    cutoff = datetime.now() - timedelta(hours=24)

    # 找出所有超过24小时未活动的会话ID
    expired_sessions = [session_id for session_id, session in sessions.items() if session['last_active'] < cutoff]

    # 删除这些会话
    for session_id in expired_sessions:
        del sessions[session_id]

def process_chat_message(message, clear_history,key,model,session_id):
    # 获取会话，如果不存在则创建一个新的会话
    session = sessions.get(session_id, {'history': [], 'last_active': datetime.now()})
    ##非缓存上下文状态则每次自动清理上下文信息
    if clear_history:
        session['history'] = []  ##清除历史信息

     # 更新会话的历史记录和最后活动时间
    if isinstance(message, str):
        print("message is str:"+message)
        me_obj =  json.loads(message)
        print(message)
    else:
        me_obj = message

    session['history'].append(me_obj)
    session['last_active'] = datetime.now()

    # 清理超过24小时未活动的会话
    cleanup_sessions()
    ##print(message)
    sessions[session_id] = session
    print(sessions)
    # 获取会话的历史记录，如果不存在则创建一个新的历史记录
    history = session['history']
    ##控制历史信息长度，删除最旧的消息
    if len(history) > MAX_HISTORY_LENGTH:
        history = history[-MAX_HISTORY_LENGTH:]
        session['history']  = history
    print(len(history) )
    print([type(m) for m in history])
    ##构建消息数组
    messages = [{"role": m['role'], "content": m['content']} for m in history if isinstance(m, dict)]
    ##messages = [{"role": m['role'], "content": m['content']} for m in history]
    # 检查消息数组是否为空
    if len(messages) == 0:
        raise ValueError("No messages available.")
    keystr = 'Bearer ' + key
    print(keystr+model)
    headers = {
        "Content-Type": "application/json",
        "Authorization": keystr
    }


    data = {
        "model": model,
        "messages": messages,
        "max_tokens": 100,
        "temperature": 0.7
    }


    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_json = response.json()

    if response.status_code == 200:
        choices = response_json["choices"]
        if len(choices) > 0:
            repaymessage = response.json()["choices"][0]["message"]
            session['history'].append(repaymessage)
            sessions[session_id] = session
            print(sessions[session_id])
            return repaymessage
            #return choices[0]["text"].strip()
        else:
            return ""
    else:
        error_message = response_json["error"]["message"] if "error" in response_json else "Unknown error"
        #raise Exception(f"Error: {response.status_code} - {error_message}")
        raise Exception(f"Error {response.status_code}: {response.text}")

##聊天接口
@app.route('/chat', methods=['POST'])
def chat():
    RaplyArr = []
    data = request.get_json()
    # session_id = request.json.get('session_id')
    session_id = data['session_id']
    message = data['message']
    clear_history = data['clear_history']
    openai_key = data['openai_key']
    model = data['model']
    if len(openai_key)<10:
        openai_key =  api_key
    if len(model)<4:
        model = modelName
     # 如果会话ID为空，则生成一个新的会话ID
    if not session_id:
        session_id = str(uuid.uuid4())

    print("session_id="+session_id)
    reply = process_chat_message(message, clear_history,openai_key,model,session_id)
    RaplyArr.append(reply)
    return RaplyArr

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)