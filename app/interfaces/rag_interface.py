class RAGInterface:
    def create_and_provision_corpus(self, files, corpus_name_suffix):
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def retrieve_context(self, corpus_id, query, top_k: int = 10, threshold: float = 0.5):
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def get_embedding(self, text, model_name: str = "", task_type: str = ""):
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def add_files_to_corpus(self, corpus_id, files):
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def remove_files_from_corpus(self, corpus_id, file_ids):
        raise NotImplementedError("This method should be overridden by subclasses.")
    

    def delete_corpus(self, corpus_id: str):
        raise NotImplementedError("This method should be overridden by subclasses.")