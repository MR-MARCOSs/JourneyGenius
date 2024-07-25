import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
import bs4
import sqlite3
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

llm = ChatOpenAI(model="gpt-3.5-turbo")

def init_db():
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')


    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_message TEXT NOT NULL,
        ai_response TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    conn.close()

def add_user(username, email):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO users (username, email) 
            VALUES (?, ?)
        ''', (username, email))
        conn.commit()
        print("Usuário adicionado com sucesso.")

    except sqlite3.IntegrityError as e:
        print(f"Erro ao adicionar usuário: {e}")

    finally:
        conn.close()

def add_conversation(user_id, user_message, ai_response):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO conversations (user_id, user_message, ai_response) 
            VALUES (?, ?, ?)
        ''', (user_id, user_message, ai_response))
        conn.commit()

    except sqlite3.IntegrityError as e:
        print(f"Erro ao adicionar conversa: {e}")

    finally:
        conn.close()

def get_chat_history(user_id):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_message, ai_response FROM conversations WHERE user_id = ? ORDER BY conversation_id
    ''', (user_id,))

    chat_history = cursor.fetchall()
    conn.close()
    

    total_characters = sum(len(msg) + len(resp) for msg, resp in chat_history)
    while total_characters > 8500 and len(chat_history) > 1:
        chat_history.pop(0)
        total_characters = sum(len(msg) + len(resp) for msg, resp in chat_history)

    return chat_history

def researchAgent(query, llm): 
    tools = load_tools(["ddg-search", "wikipedia"], llm=llm)

    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(
        llm,
        tools,
        prompt
    )

    agent_executor = AgentExecutor(agent=agent, tools=tools, prompt=prompt, verbose=True, handle_parsing_errors=True)
    webContext = agent_executor.invoke({"input": query})
    return webContext['output']

def supervisorAgent(query, llm, webContext, chat_history):
    prompt_template= """
    Você é o agente de viagens JourneyGenius. Sua resposta final deverá ser um roteiro de viagem completo e detalhado OU a continuação da conversa com o usuário.
    Verifique primeiramente o histórico de conversa até o momento e o input
    Utilize o contexto de eventos(se for útil), preços de passagens, input do usuário para elaborar o roteiro.
    Histórico: {chat_history}
    Usuário: {query}
    Contexto: {webContext}
    
    JourneyGenius:
    """


    formatted_chat_history = "\n".join(
        f"Usuário: {msg}\nAssistente: {resp}" for msg, resp in chat_history
    )

    prompt = PromptTemplate(
        input_variables= ['webContext', 'query', 'chat_history'],
        template=prompt_template
    )

    sequence = RunnableSequence(
        prompt | llm
    )

    response = sequence.invoke({"webContext": webContext, "query": query, "chat_history": formatted_chat_history})
    return response

def getResponse(llm, user_id):
    msg_count = 1
    query = input("Diga: ")

    webContext = researchAgent(query, llm)


    chat_history = get_chat_history(user_id)

    response = supervisorAgent(query, llm, webContext, chat_history)


    add_conversation(user_id, query, response.content)

    return response


init_db()


user_id = 1   

print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
print(getResponse(llm, user_id).content)
print("finish")
