from langchain.prompts.chat import(
    ChatMessagePromptTemplate,
    SystemMessagePromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)
from langchain.prompts import PromptTemplate
template="you {input_language}{output_language}"
system_message_prompt=SystemMessagePromptTemplate.from_template(template)
human_template="{text}"
humen_message_prompt=HumanMessagePromptTemplate.from_template(human_template)
chat_prompt=ChatPromptTemplate.from_messages([system_message_prompt,humen_message_prompt])
chat_prompt.format_messages(input_language="en",output_language="English",output_language="French")

from langchain.llms import OpenAI

llm=OpenAI(model="gpt-3.5-turbo")
llm.prompt=chat_prompt
template1="please provide a {topic}"
prompt=PromptTemplate(input_variables=["topic"],template=template1)
prompt.from_template(topic="summary")