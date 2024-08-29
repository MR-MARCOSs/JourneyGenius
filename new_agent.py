from langchain import hub

from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents import Tool, initialize_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

model = ChatOpenAI(model="gpt-4o")

def process_interaction(query, model):
    search = DuckDuckGoSearchRun()
    tools = [search]

    template = """You are a nice chatbot having a conversation with a human.

    Previous conversation:
    {chat_history}

    New human question: {question}
    Response:"""

    prompt = PromptTemplate.from_template(template)
    memory = ConversationBufferWindowMemory(
        memory_key='chat_history',
        k=3,
        return_messages=True,
    )
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
