from langchain import hub

from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents import Tool, initialize_agent
from langchain.memory import ConversationBufferWindowMemory  # Classe base para ferramentas
from langchain_openai import ChatOpenAI
# Removido a importação duplicada e desnecessária de load_tools
from langchain_core.prompts import PromptTemplate


# Configura o modelo model
model = ChatOpenAI(model="gpt-4o")


def process_interaction(query, model):
    search = DuckDuckGoSearchRun()
    tools = [search]
    memory = ConversationBufferWindowMemory(
        memory_key='chat_history',
        k=3,
        return_messages=True,
    )
    prompt = hub.pull('hwchase17/openai-functions-agent')
    conversational_agent = create_openai_functions_agent(
        prompt=prompt,
        tools=tools,
        llm=model,
    )
    agent_executor = AgentExecutor(agent=conversational_agent, tools=tools, verbose=True, max_iterations=3, early_stopping_method='generate', memory=memory)
    agent_executor.invoke({'input':query})



query = input("Sua mensagem: ")

try:
    response = process_interaction(query, model)
    print("Resposta do assistente:", response)
except ValueError as e:
    print("Erro:", e)
