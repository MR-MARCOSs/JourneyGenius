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

OPENAI_API_KEY= os.environ['OPENAI_API_KEY']

llm = ChatOpenAI(model="gpt-3.5-turbo")

def researchAgent(query,llm): 
    tools = load_tools(["ddg-search", "wikipedia"], llm=llm)
    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(
        llm,
        tools,
        prompt
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, prompt=prompt, verbose=True )
    webContext = agent_executor.invoke({"input": query})
    return webContext['output']

def supervisorAgent(query, llm, webContext):
    prompt_template= """
    Você é um agente de viagens. Sua resposta final deverá ser um roteiro de viagem completo e detalhado.
    Utilize o contexto de eventos e preços de passagens e o input do usuário para elaborar o roteiro.
    Contexto: {webContext}
    Usuário: {query}
    Assistente: 
    """
    prompt = PromptTemplate(
        input_variables= ['webContext', 'query'],

        
        template = prompt_template
    )
    sequence = RunnableSequence(
        prompt | llm
    )
    response = sequence.invoke({"webContext": webContext, "query": query})
    return response

def getResponse(query, llm):
    webContext = researchAgent(query, llm)
   
    response = supervisorAgent(query, llm, webContext)
    return response

def lambda_handler(event, context):
    body = json.loads(event.get('body', {}))
    query = body.get('question', 'Parâmetro question não fonecido')
    response = getResponse(query,llm).content
    return {
            "statusCode": 200,
            "header": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Tarefa concluída com sucesso",
                "details": response,
            })
            }