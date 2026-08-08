import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

class BaseGraphLoader(ABC):
    """Abstract base for all graph database loaders."""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def create_schema(self):
        pass
    
    @abstractmethod
    def load_nodes(self, nodes):
        """nodes: list of dicts with 'id' and optional 'label'"""
        pass
    
    @abstractmethod
    def load_edges(self, edges):
        """edges: list of dicts with 'source', 'target', and optional 'type'"""
        pass
    
    @abstractmethod
    def clear_data(self):
        pass
    
    @abstractmethod
    def close(self):
        pass
