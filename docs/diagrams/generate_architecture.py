import os
# Add Graphviz to PATH for Windows if not present (common issue after fresh install without restart)
os.environ["PATH"] += os.pathsep + r'C:\Program Files\Graphviz\bin'

from diagrams import Diagram, Cluster, Edge
from diagrams.azure.compute import AppServices, VM
from diagrams.azure.ml import CognitiveServices
from diagrams.onprem.client import User
from diagrams.onprem.container import Docker
from diagrams.onprem.compute import Server
from diagrams.programming.language import Python
from diagrams.generic.storage import Storage
from diagrams.onprem.search import Solr # Using Solr as a proxy for Meilisearch if direct icon not available
from diagrams.custom import Custom

# Note: You might need to install specific providers:
# pip install diagrams

graph_attr = {
    "fontsize": "24",
    "bgcolor": "transparent"
}

with Diagram("Microsoft RAG Smart Retrieval System", show=False, filename="rag_architecture", graph_attr=graph_attr, direction="LR"):
    
    user = User("User\n(Input/Output)")

    with Cluster("Azure Cloud Environment"):
        
        with Cluster("App Service Plan"):
            web_app = AppServices("App Service B1\n(Flask 3.0.3 + Python 3.11)\nFrontend: HTML+JS")
        
        aoai = CognitiveServices("Azure OpenAI Service\n(GPT-4o-mini)")

        # Link App Service to AOAI
        web_app >> Edge(label="API Call\n(Chat/RAG)") >> aoai

    with Cluster("Search Engine Infrastructure (Docker/VM)"):
        vm = VM("Linux VM\n(vCPU 2, RAM 8G)")
        
        with Cluster("Docker Container"):
            with Cluster("LLM Service"):
                ollama = Server("Ollama LLM\n(bge-m3 Embedding)\nPort: 11434")
            
            with Cluster("Vector DB"):
                # Using Solr icon as generic search/vector DB representation since Meilisearch icon might be missing in older versions
                # Or use custom if available. For standard diagrams, Solr/Elastic is often used.
                meili = Solr("Meilisearch\n(Hybrid Search)\nPort: 7700")

    with Cluster("Local Environment (Data ETL)"):
        local_server = Server("Local Server\n(RTX4050, 32G RAM)\nPython Env")
        
        with Cluster("ETL Pipeline"):
            scheduler = Python("Scheduler.py\n(Daily 06:00)")
            crawler = Python("Web Crawlers")
            cleaner = Python("Data Cleaner")
            vectorizer = Python("Vector Upload")
            
            scheduler >> crawler >> cleaner >> vectorizer

    # Wiring the High Level Connections
    
    # User flow
    user >> Edge(label="Search Request") >> web_app
    web_app >> Edge(label="Search Results") >> user
    
    # App Service to Search Engine
    web_app >> Edge(label="Embedding Req") >> ollama
    web_app >> Edge(label="Search Query") >> meili
    meili >> Edge(label="Return Results") >> web_app
    
    # Local to Search Engine (Data Sync)
    vectorizer >> Edge(label="Sync Vectors\n(Upsert)") >> meili

