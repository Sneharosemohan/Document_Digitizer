![image](https://github.com/user-attachments/assets/a5e7cb72-d57b-470f-95c4-4046f675783c)# Document_Digitizer
The Document Digitizer represents a sophisticated solution for efficiently extracting textual content, signatures, and seals from various documents while ensuring their authenticity. By incorporating leading-edge AI technologies and intelligent agent orchestration frameworks such as NVIDIA Agent IQ and CrewAI, alongside MCP protocols, it optimizes digital workflows to deliver enhanced accuracy and robust security in document processing.
## Tech Stack
The Document Digitizer is built on a robust and versatile tech stack that ensures optimal functionality and adaptability. Key components of the tech stack include:
•	NVIDIA Agent IQ / CrewAI: Utilizes intelligent agent frameworks like NVIDIA Agent IQ and CrewAI for orchestrating workflows and enabling smart automation.
•	Model Context Protocol (MCP): Provides a standardized protocol to replace fragmented integrations, facilitating reliable and efficient connections to advanced AI models.
•	NIM Vision Language Models (VLM): Leverages vision language models to enhance the capabilities of intelligent data extraction.
•	LangChain: Enables the creation of complex workflows and integrations for seamless data processing.
•	FastAPI: Supports the development of lightweight and high-performance APIs for secure and scalable operations.
## Key Benefits
The Document Digitizer offers several advantages that make it indispensable for modern document processing:
•	Agentic Orchestration: Provides a modular and secure architecture for intelligent orchestration, streamlining operations.
•	Unified Integration: The MCP protocol ensures seamless integration with various AI models, eliminating the need for fragmented systems.
•	Reduced Manual Effort: Automation of extraction and verification processes minimizes human intervention, significantly saving time and resources.
•	Intelligent Data Handling: Multimodal AI enhances the ability to extract and process data intelligently, even inferring missing information for accuracy.
•	Enhanced Security: The system follows best practices to safeguard sensitive information during document processing.  

<img width="1085" alt="DD_Architectural_Diagram" src="https://github.com/user-attachments/assets/74457962-a7d9-4661-a95f-210f477262bf" />

## Steps to Run Document Digitizer
1.**Clone the Repository and Start MongoDB**
  Clone this repository to your local machine.
  Ensure your MongoDB server is running.
 
2. **Install NVIDIA AgentIQ Toolkit**
  Follow the official instructions as per the official documentation : https://github.com/NVIDIA/AIQToolkit

3. **Activate the Python Virtual Environment and Set Environment Variables**
   Activate your .venv as per the installation steps.
   Export the required environment variables:
     export NVIDIA_API_KEY=nvapi-...
     export MEM0_API_KEY=m0-...

4. **Install Python Requirements**
  Navigate to the mcp_dd folder and install dependencies:
    pip install -r mcp_dd/requirements.txt

5. **Add Environment Variables to .env File**
   In your .env file, add:
     LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY=nvapi-...

6. **Start the MCP Server**
   Run the following command: python mcp_dd/dd_mcp_server.py

7. **Start the NVIDIA AIQ Server**
   Use the serve command: aiq serve --config_file dd_aiq_workflow/src/dd_aiq_workflow/configs/config.yml

**Note**:
Replace nvapi-... and m0-... with your actual API keys.
Make sure all dependencies are installed and environment variables are set before starting the servers.---
If you intend to use the email feature, update the sender email and password in mcp_dd/dd_mcp_server.py with your own credentials before running the application.

