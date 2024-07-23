import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
import bs4
import json
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

import requests

class Llama3:
    def __init__(self, url="http://localhost:11434/api/generate"):
        self.url = url

    def predict(self, prompt):
        data = {"model": "llama3", "prompt": prompt}
        response = requests.post(self.url, json=data)
        return response.json()["choices"][0]["text"]




llm = Llama3()

query = """
    Vou viajar para Tokyo em Agosto de 2024
    Quero que faça um roteiro de viagens para mim com eventos que irão ocorrer na data da viagem e com o preço da passagem
"""

def researchAgent(query, llm):
    tools = load_tools(["ddg-search", "wikipedia"], llm=llm)

    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(
        llm,
        tools,
        prompt
    )

    agent_executor = AgentExecutor(agent=agent, tools=tools, prompt=prompt, verbose=True)
    webContext = agent_executor.invoke({"input": query})
    return webContext['output']

def loadData():
    loader = WebBaseLoader(
        web_paths=("https://www.dicasdeviagem.com/inglaterra/",),
        bs_kwargs=dict(parse_only=bs4.SoupStrainer(class_=("postcontentwrap", "pagetitleloading background-imaged loading-dark")))
    )
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

def supervisorAgent(query, llm, webContext, relevant_documents):
    prompt_template = """
    Você é um agente de viagens. Sua resposta final deverá ser um roteiro de viagem completo e detalhado.
    Utilize o contexto de eventos e preços de passagens, o input do usuário e também os documentos relevantes para elaborar o roteiro.
    Contexto: {webContext}
    Documento relevante: {relevant_documents}
    Usuário: {query}
    Assistente: 
    """

    prompt = PromptTemplate(
        input_variables=['webContext', 'relevant_documents', 'query'],
        template=prompt_template
    )

    sequence = RunnableSequence(
        prompt | llm
    )

    response = sequence.invoke({"webContext": webContext, "relevant_documents": relevant_documents, "query": query})
    return response

def getResponse(query, llm):
    webContext = researchAgent(query, llm)
    relevant_documents = getRelevantDocs(query)
    response = supervisorAgent(query, llm, webContext, relevant_documents)
    return response

print("\n\n\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
print(getResponse(query, llm))
print("finish")