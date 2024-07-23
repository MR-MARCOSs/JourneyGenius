import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.document_loaders import *
from langchain_community.vectorstores import Chroma
import bs4
from langchain_text_splitters.character import CharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence


llm = ChatOpenAI(model="gpt-3.5-turbo")

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


def loadData(chat_history):
    loader= 
    documents = loader.load()
    print("3")
    docs = chat_history
    print("4")
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)

    print("5")

    print("6")
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings())
    print("7")
    retriever = vectorstore.as_retriever()
    print("8")
    return retriever

def getRelevantDocs(query, chat_history):
    print("1")
    retriever = loadData(chat_history)
    print("2")
    relevant_documents = retriever.invoke(query)
    print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _docs")
    print(relevant_documents)
    print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _docs")
    return relevant_documents

def supervisorAgent(query, llm, webContext, relevant_docs):
    prompt_template= """
    Você é o agente de viagens JourneyGenius. Sua resposta final deverá ser um roteiro de viagem completo e detalhado ou a continuação da conversa com o usuário.
    Utilize o contexto de eventos(se for útil), preços de passagens, input do usuário para elaborar o roteiro e o histórico de conversa até o momento.

    Contexto: {webContext}
    Usuário: {query}
    Histórico: {relevant_docs}
    Assistente: 
    """

    prompt = PromptTemplate(
        input_variables= ['webContext', 'relevant_documents', 'query', 'chat_history'],
        template = prompt_template
    )

    sequence = RunnableSequence(
        prompt | llm
    )

    response = sequence.invoke({"webContext": webContext, "query": query, "relevant_docs": relevant_docs})
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
        print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
        print(chat_history)
        query = input("Diga: ")
        webContext = researchAgent(query, llm)
        relevant_docs=getRelevantDocs(query,chat_history)
        response = supervisorAgent(query, llm, webContext, relevant_docs)
        chat_history["Humano"].append(f"{msg_count}ª mensagem:" + query)
        chat_history["Você"].append(f"Tua resposta a {msg_count}ª mensagem:"+response.content)
        msg_count+=1
    
    return response


print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
print(getResponse(llm).content)
print("finish")