import sqlite3
import json
from langchain.chains import LLMMathChain
from langchain.tools import Tool
from langchain.agents import load_tools, initialize_agent
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
#from duckduckgo_search import DDGS
from duckduckgo_search import DDGS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

# Configura o modelo model
model = ChatOpenAI(model="gpt-3.5-turbo")



def init_db():
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        token TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat (
        chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_message TEXT NOT NULL,
        ai_response TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    conn.close()

def add_user(username, token):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, token) 
            VALUES (?, ?)
        ''', (username, token))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"Erro ao adicionar usuário: {e}")
    finally:
        conn.close()

def get_user_id(username, token):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE token = ? AND username = ?', (token, username))
    user_record = cursor.fetchone()
    cursor.execute('SELECT user_id FROM users WHERE token = ?', (token,))
    ver = cursor.fetchone()

    if ver is None:
        add_user(username, token)
        cursor.execute('SELECT user_id FROM users WHERE token = ?', (token,))
        user_record = cursor.fetchone()
    
    elif user_record != ver:
        raise ValueError("Token already exists")

    conn.close()
    return user_record[0]

def add_chat(user_id, user_message, ai_response):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM chat WHERE user_id = ?', (user_id,))
    message_number = cursor.fetchone()[0] + 1
    cursor.execute('SELECT user_message, ai_response FROM chat WHERE user_id = ?', (user_id,))
    all_chat = cursor.fetchall()
    carac_count = str(all_chat)
    formatted_user_message = f"{message_number}º mensagem: {user_message}"
    formatted_ai_response = f"tua resposta a {message_number}º mensagem: {ai_response}"

    try:
        cursor.execute('''
            INSERT INTO chat (user_id, user_message, ai_response) 
            VALUES (?, ?, ?)
        ''', (user_id, formatted_user_message, formatted_ai_response))
        conn.commit()
    finally:
        while len(carac_count) > 7000:
            cursor.execute('DELETE FROM chat WHERE chat_id = (SELECT MIN(chat_id) FROM chat)')
            cursor.execute('SELECT user_message, ai_response FROM chat WHERE user_id = ?', (user_id,))
            all_chat = cursor.fetchall()
            carac_count = str(all_chat)
            conn.commit()
        conn.close()

def get_chat_history(user_id):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_message, ai_response FROM chat WHERE user_id = ? ORDER BY chat_id
    ''', (user_id,))
    chat_history = cursor.fetchall()
    conn.close()
    return chat_history

def supervisorAgent(query, model_with_tools, chat_history):
    prompt_template = """
    Você é o agente de viagens JourneyGenius. Sua resposta final deverá ser um roteiro de viagem completo e detalhado ou a continuação da conversa com o usuário.
    Utilize o contexto de eventos(se for útil), preços de passagens, o histórico da conversa com você até o momento e principalmente o input do usuário.

    Usuário: {query}
    Histórico: {chat_history} 
    """

    prompt = PromptTemplate(
        input_variables=['query', 'chat_history'],
        template=prompt_template
    )
    sequence = RunnableSequence(prompt | model_with_tools)
    response = sequence.invoke({"query": query, "chat_history": chat_history})

    print(f"Content: {response['content']}")
    print(f"Tool calls: {json.dumps(response['tool_calls'], indent=2)}")
    return response

def process_interaction(username, token, query):
    search = DDGS().text(query) 
    tools = [
        Tool(
            name="ddg-search",
            description="A tool for searching the web using DuckDuckGo.",
            func=search.run,  
        ),
    ]
    model_with_tools=model.bind_tools(tools)
    user_id = get_user_id(username, token)
    #webContext = model_tools(query, model_with_tools)
    chat_history = get_chat_history(user_id)
    response = supervisorAgent(query, model_with_tools, chat_history)
    add_chat(user_id, query, response.content)
    return response.content
init_db()

username = input("Nome de usuário: ")
token = input("Token: ")
query = input("Sua mensagem: ")

try:
    response = process_interaction(username, token, query)
    print("Resposta do assistente:", response)
except ValueError as e:
    print("Erro:", e)
