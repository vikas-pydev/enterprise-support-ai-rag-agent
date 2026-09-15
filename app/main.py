from app.conversation import Conversation


def main():
    conversation = Conversation()

    while True:
        question = input("\nYou: ")

        if question.lower() == "exit":
            break

        answer = conversation.ask(question)

        print("\nAI:", answer)


if __name__ == "__main__":
    main()