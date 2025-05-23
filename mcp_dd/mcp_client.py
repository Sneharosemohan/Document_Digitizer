import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
load_dotenv()

# for agents
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from langchain_nvidia_ai_endpoints import ChatNVIDIA

NVIDIA_API_KEY = os.getenv('LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY')

model = ChatNVIDIA(model="meta/llama-3.3-70b-instruct", temperature=0)

# SYSTEM_PROMPT = """\
# You are an AI assistant for extracting data from documents.
# Before you help a user, you need to work with tools to identify which tool to use.
# """


async def main():
    server_params = StdioServerParameters(
        command = "python",
        args = ["mcp_dd/dd_mcp_server.py"]
    )

    async with stdio_client(server_params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            response = await session.list_tools()
            print("Available tools: ", [tool.name for tool in response.tools])

            # result = await session.call_tool("extract_data", {"object_id": "68105c264dcb0aa6ca999ad8"})
            # print("Extraction result: ", result.content[0].text)

            result = await session.call_tool("compare_face_images", {"object_id_1": "681ca3854715144008ad0be9", "object_id_2": "681ca3854715144008ad0bea"})
            print("Comparison results: ", result.content[0].text)
            # result = await session.call_tool("get_attachment_name_by_id", {"objectId": "68105c264dcb0aa6ca999ad8"})
            # print("Attachment name: ", result.content[0].text)
            
            # result = await session.call_tool("ask_question", {"json_data": "{'name':'Sneha','age':'90'}", "question":"What is the employee name"})
            # print("Employee name: ", result.content[0].text)
            # save_file_result = await session.call_tool("save_text_PDF", {"text": result.content[0].text, "file_name": "temp_topic.pdf"})
            # print("Saving result: ", save_file_result.content)
            # tools = await load_mcp_tools(session)

            # agent = create_react_agent(model, tools)
            # agent_response = await agent.ainvoke({"messages": "Write a detailed blog post about: How to use NVIDIA AI endpoints for content generation?"})
            # print("Agent response: ", agent_response['messages'][-1].content)
            # return agent_response


    # # #run agent using langchain libraries
    # async with stdio_client(server_params) as (read, write):

    #     async with ClientSession(read, write) as session:

    #         await session.initialize()

    #         print("MCP Session Initialized.")

    #         tools = await load_mcp_tools(session)
            

    #         print(f"Loaded Tools: {[tool.name for tool in tools]}")

    #         agent = create_react_agent(model, tools)

    #         print("ReAct Agent Created.")

    #         print(f"Invoking agent with query")

    #         response = await agent.ainvoke({

    #             "messages": [("user", "What is NVIDIA NIM?")]

    #         })

    #         print("Agent invocation complete.")
    #         print("Response from agents : ", response["messages"][-1].content)
    #         # Return the content of the last message (usually the agent's final answer)

    #         return response["messages"][-1].content



if __name__ == "__main__":
    asyncio.run(main())