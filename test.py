from agent.chatbot import build_hr_graph

hr_agent = build_hr_graph()

if __name__ == "__main__":

    print("HR Assistant is ready. Type 'exit' to stop.\n")

    thread_id = "session_1"

    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            break

        result = hr_agent.invoke(
            {"question": user_input},
            config={"configurable": {"thread_id": thread_id}}
        )

        print("\nHR Assistant:")
        print(result.get("final_answer"))
        print()
