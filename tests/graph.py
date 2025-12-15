from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import dotenv_values 

config = dotenv_values(".env")
API_KEY = config["API_KEY"]

class GraphState(TypedDict):
    question: str
    answer: str

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key=API_KEY
)

prompt = PromptTemplate(
    input_variables=["question"],
    template="Answer the question clearly:\n{question}"
)

chain = prompt | llm

def llm_node(state: GraphState) -> GraphState:
    result = chain.invoke({"question": state["question"]})
    return {
        "answer": result.content
    }

graph = StateGraph(GraphState)

graph.add_node("llm", llm_node)
graph.set_entry_point("llm")
graph.add_edge("llm", END)

app = graph.compile()

final_state = app.invoke({
    "question": "What is the difference between AI and ML?"
})

print(final_state["answer"])
