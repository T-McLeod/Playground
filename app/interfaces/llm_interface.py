class LLMInterface:
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def generate_answer(self, query: str, context: str = None, model_name: str = "") -> list:
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def summarize_file(self, file_path: str, prompt: str = "", model_name: str = "") -> str:
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def generate_suggested_questions(self, topic: str, count: int = 3, model_name: str = "") -> list:
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def summarize_topic(self, topic: str, context: list[str], model_name: str = "") -> str:
        raise NotImplementedError("This method should be overridden by subclasses.")