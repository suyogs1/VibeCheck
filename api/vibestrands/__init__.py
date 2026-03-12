from .models import BedrockModel

class Response:
    def __init__(self, text):
        self.text = text

class Agent:
    def __init__(self, name: str, model, system_prompt: str):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.history = []

    def invoke(self, message: str) -> Response:
        self.history.append({"role": "user", "content": [{"text": message}]})
        
        system = [{"text": self.system_prompt}]
        
        response_text = self.model.converse(system, self.history)
        
        self.history.append({"role": "assistant", "content": [{"text": response_text}]})
        
        return Response(response_text)
