import logging

from pydantic import Field

from aiq.builder.builder import Builder
from aiq.builder.function_info import FunctionInfo
from aiq.cli.register_workflow import register_function
from aiq.data_models.function import FunctionBaseConfig

logger = logging.getLogger(__name__)


## This is a template for creating a new function in the AIQ Toolkit.
class DdWorkflowFunctionConfig(FunctionBaseConfig, name="dd_workflow"):
    """
    AIQ Toolkit function template. Please update the description.
    """
    # Add your custom configuration parameters here
    parameter: str = Field(default="default_value", description="Notional description for this parameter")


@register_function(config_type=DdWorkflowFunctionConfig)
async def dd_workflow_function(
    config: DdWorkflowFunctionConfig, builder: Builder
):
    # Implement your function logic here
    async def _response_fn(input_message: str) -> str:
        # Process the input_message and generate output
        output_message = f"Hello from dd_workflow workflow! You said: {input_message}"
        return output_message

    try:
        yield FunctionInfo.create(single_fn=_response_fn)
    except GeneratorExit:
        print("Function exited early!")
    finally:
        print("Cleaning up dd_workflow workflow.")

##########################################################################
# The following code is a template for creating a new function for adding the memory module to the AIQ Toolkit.


# from aiq.data_models.memory import MemoryBaseConfig
# from aiq.memory.interfaces import MemoryEditor, MemoryItem
from aiq.data_models.component_ref import MemoryRef
from aiq.memory.models import MemoryItem
from aiq.memory.models import SearchMemoryInput

class DDAddToolConfig(FunctionBaseConfig, name="dd_add_memory"):
    """Function to add memory to a hosted memory platform."""

    description: str = Field(default=("Tool to add memory about a user's conversational queries to a system "
                                      "for retrieval later."),
                             description="The description of this function's use for tool calling agents.")
    memory: MemoryRef = Field(default="saas_memory",
                              description=("Instance name of the memory client instance from the workflow "
                                           "configuration object."))


@register_function(config_type=DDAddToolConfig)
async def dd_add_memory_tool(config: DDAddToolConfig, builder: Builder):
    """
    Function to add memory to a hosted memory platform.
    """

    from langchain_core.tools import ToolException

    # First, retrieve the memory client
    memory_editor = builder.get_memory_client(config.memory)

    async def _arun(item: MemoryItem) -> str:
        """
        Asynchronous execution of addition of memories.
        """

        try:

            await memory_editor.add_items([item])

            return "Memory added successfully. You can continue. Please respond to the user."

        except Exception as e:

            raise ToolException(f"Error adding memory: {e}") from e

    yield FunctionInfo.from_fn(_arun, description=config.description)

##########################################
class DDGetToolConfig(FunctionBaseConfig, name="dd_get_memory"):
    """Function to get memory to a hosted memory platform."""

    description: str = Field(default=("Tool to retrieve memory about a user's "
                                      "interactions to help answer questions in a personalized way."),
                             description="The description of this function's use for tool calling agents.")
    memory: MemoryRef = Field(default="saas_memory",
                              description=("Instance name of the memory client instance from the workflow "
                                           "configuration object."))


@register_function(config_type=DDGetToolConfig)
async def dd_get_memory_tool(config: DDGetToolConfig, builder: Builder):
    """
    Function to get memory to a hosted memory platform.
    """

    import json

    from langchain_core.tools import ToolException

    # First, retrieve the memory client
    memory_editor = builder.get_memory_client(config.memory)

    async def _arun(search_input: SearchMemoryInput) -> str:
        """
        Asynchronous execution of collection of memories.
        """
        try:
            memories = await memory_editor.search(
                query=search_input.query,
                top_k=search_input.top_k,
                user_id=search_input.user_id,
            )

            memory_str = f"Memories as a JSON: \n{json.dumps([mem.model_dump(mode='json') for mem in memories])}"
            return memory_str

        except Exception as e:

            raise ToolException(f"Error retreiving memory: {e}") from e

    yield FunctionInfo.from_fn(_arun, description=config.description)
