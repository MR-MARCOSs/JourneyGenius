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
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS human_message
              id VARCHAR(16) PRIMARY KEY,
              message_number INT AUTOINCREMENT,
              humam_message TEXT,
              
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS response_from_ai
              id_message VARCHAR(16) NOT NULL,
              response_from_ai TEXT,
              FOREIGN KEY (id_mensage) REFERENCES human_message (id)
    ''')
    conn.commit()
    conn.close()

def add_message(id, human_message, response_from_ai):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute(
        '''
    INSERT INTO human_message (id, human_message)
    VALUES (:id, :human_message)
    ''', {
        'id': id,
        'human_message': human_message
    }
    ),
    c.execute(
        '''
    INSERT INTO response_from_ai (id, response_from_ai)
    VALUES (:id, :response_from_ai)
    ''', {
        'id': id,
        'response_from_ai': response_from_ai
    })





def researchAgent(query,llm): 


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

'''
def loadData():
    loader = WebBaseLoader(
    web_paths=("https://www.dicasdeviagem.com/inglaterra/",),
    bs_kwargs=dict(parse_only=bs4.SoupStrainer(class_=("postcontentwrap", "pagetitleloading background-imaged loading-dark"))))
    print("3")
    docs = loader.load()
    print("4")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    print("5")
    splits = text_splitter.split_documents(docs)
    print("6")
    vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())
    print("7")
    retriever = vectorstore.as_retriever()
    print("8")
    return retriever

def getRelevantDocs(query):
    print("1")
    retriever = loadData()
    print("2")
    relevant_documents = retriever.invoke(query)
    print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
    print(relevant_documents)
    return relevant_documents
'''
def supervisorAgent(query, llm, webContext, chat_history):
    prompt_template= """
    Você é o agente de viagens JourneyGenius. Sua resposta final deverá ser um roteiro de viagem completo e detalhado ou a continuação da conversa com o usuário.
    Utilize o contexto de eventos(se for útil), preços de passagens, input do usuário para elaborar o roteiro e o histórico de conversa até o momento.

    Contexto: {webContext}
    Usuário: {query}
    Histórico: {chat_history}
    Assistente: 
    """

    prompt = PromptTemplate(
        input_variables= ['webContext', 'relevant_documents', 'query', 'chat_history'],
        template = prompt_template
    )

    sequence = RunnableSequence(
        prompt | llm
    )

    response = sequence.invoke({"webContext": webContext, "query": query, "chat_history": chat_history})
    return response

def getResponse(llm):
    chat_history = {
        "Humano": [],
        "Você": []
    }
    msg_count=1
    while True:
        
        while True:
            number_of_human_characters = sum(len(msg) for msg in chat_history["Humano"])
            number_of_ai_characters = sum(len(msg) for msg in chat_history["Você"])
            total_characters = number_of_human_characters+number_of_ai_characters
            print("antes")
            print(total_characters)
            print(len(chat_history["Humano"]))
            while total_characters > 8500:
                del chat_history["Humano"][0]
                del chat_history["Você"][0]
                number_of_human_characters = sum(len(msg) for msg in chat_history["Humano"])
                number_of_ai_characters = sum(len(msg) for msg in chat_history["Você"])
                total_characters = number_of_human_characters+number_of_ai_characters
                if  len(chat_history["Humano"])==1:
                    break
            break
        print("dps")
        print(total_characters)
        print(len(chat_history["Humano"]))            
        print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n\n _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
        print(chat_history)
        query = input("Diga: ")
        webContext = researchAgent(query, llm)

        response = supervisorAgent(query, llm, webContext, chat_history)
        chat_history["Humano"].append(f"{msg_count}ª mensagem:" + query)
        chat_history["Você"].append(f"Tua resposta a {msg_count}ª mensagem:"+response.content)
        msg_count+=1
    
    return response


print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
print(getResponse(llm).content)
print("finish")