from app.llm import ask_llm


class Conversation:
    def __init__(self):
        self.messages = []

    def add_user_message(self, message: str):
        self.messages.append({
            "role": "user",
            "content": message,
        })

    def add_assistant_message(self, message: str):
        self.messages.append({
            "role": "assistant",
            "content": message,
        })

    def ask(self, question: str) -> str:
        self.add_user_message(question)

        answer = ask_llm(self.messages)

        self.add_assistant_message(answer)

        return answer