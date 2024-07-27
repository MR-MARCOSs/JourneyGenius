import sqlite3
import secrets
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

# Inicializa o modelo de linguagem
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Inicializa o banco de dados
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
    CREATE TABLE IF NOT EXISTS conversations (
        conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_message TEXT NOT NULL,
        ai_response TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    conn.close()

# Adiciona um usuário ao banco de dados
def add_user(username, token):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO users (username, token) 
            VALUES (?, ?)
        ''', (username, token))
        conn.commit()
        print("Usuário adicionado com sucesso.")

    except sqlite3.IntegrityError as e:
        print(f"Erro ao adicionar usuário: {e}")

    finally:
        conn.close()

# Obtém o ID de usuário associado ao token e ao nome de usuário fornecidos
def get_user_id(username, token):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE token = ? AND username = ?', (token, username))
    user_record = cursor.fetchone()
    cursor.execute('SELECT * FROM users WHERE token = ?', (token,))
    ver = cursor.fetchone()
    print(user_record)
    #print(user_record[0])

    if ver is None:
        # Cadastra um novo usuário se o token não existir
        add_user(username, token)
        cursor.execute('SELECT user_id FROM users WHERE token = ?', (token,))
        user_record = cursor.fetchone()
    
    elif user_record!=ver:
        raise ValueError("Token already exists")   
        # Erro se o token existe mas está associado a um nome de usuário diferente
    conn.close()
    return user_record[0]

# Adiciona uma conversa ao banco de dados
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

# Obtém o histórico de conversas do usuário
def get_chat_history(user_id):
    conn = sqlite3.connect('JourneyGenius.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_message, ai_response FROM conversations WHERE user_id = ? ORDER BY conversation_id
    ''', (user_id,))

    chat_history = cursor.fetchall()
    conn.close()
    
    # Limita o tamanho do histórico
    total_characters = sum(len(msg) + len(resp) for msg, resp in chat_history)
    while total_characters > 8500 and len(chat_history) > 1:
        chat_history.pop(0)
        total_characters = sum(len(msg) + len(resp) for msg, resp in chat_history)

    return chat_history

# Realiza a pesquisa do agente de viagem
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

# Gera a resposta do agente supervisor
def supervisorAgent(query, llm, webContext, chat_history):
    prompt_template= """
    Você é o agente de viagens JourneyGenius. Sua resposta final deverá ser um roteiro de viagem completo e detalhado ou a continuação da conversa com o usuário.
    Utilize o contexto de eventos(se for útil), preços de passagens, input do usuário para elaborar o roteiro e o histórico de conversa até o momento.

    Contexto: {webContext}
    Usuário: {query}
    Histórico: {chat_history}
    Assistente: 
    """

    # Formata o histórico de chat para o prompt
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

# Processa a interação do usuário com o agente
def process_interaction(username, token, query):
    # Obtém o ID do usuário ou cadastra-o
    user_id = get_user_id(username, token)

    # Realiza a pesquisa do agente
    webContext = researchAgent(query, llm)

    # Obtém o histórico de chat do banco de dados
    chat_history = get_chat_history(user_id)

    # Gera a resposta do supervisor
    response = supervisorAgent(query, llm, webContext, chat_history)

    # Adiciona a nova interação ao banco de dados
    add_conversation(user_id, query, response.content)

    return response.content

# Inicializa o banco de dados
init_db()

# Exemplo de interação
username = input("Nome de usuário: ")
token = input("Token: ")
query = input("Sua mensagem: ")

try:
    response = process_interaction(username, token, query)
    print("Resposta do assistente:", response)
except ValueError as e:
    print("Erro:", e)
