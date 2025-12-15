from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import dotenv_values 

config = dotenv_values(".env")
API_KEY = config["API_KEY"]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key=API_KEY
)

# Prompt template
prompt = PromptTemplate(
    input_variables=["question"],
    template="Answer the question clearly:\n{question}"
)

# LCEL chain
chain = prompt | llm

# Invoke
result = chain.invoke({
    "question": "What is the difference between AI and ML?"
})

print(result.content)
