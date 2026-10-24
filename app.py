
import gradio as gr
import csv
import io
import re
from datetime import datetime
from difflib import SequenceMatcher

INITIAL_FAQS = [
    {
        "question": "What services do you offer?",
        "answer": "We offer business consulting, digital marketing, and customer support.",
        "category": "Services"
    },
    {
        "question": "What are your business hours?",
        "answer": "We are open Monday to Saturday, 9 AM to 6 PM.",
        "category": "General"
    },
    {
        "question": "How can I contact support?",
        "answer": "Email support@example.com for assistance.",
        "category": "Support"
    },
    {
        "question": "What payment methods do you accept?",
        "answer": "We accept credit cards, debit cards, UPI, and bank transfers.",
        "category": "Payments"
    },
    {
        "question": "What is your refund policy?",
        "answer": "Refund requests must be submitted within 7 days, subject to our policy.",
        "category": "Payments"
    },
    {
        "question": "Do you offer discounts?",
        "answer": "NO! we dont offer any discounts.",
        "category": "Sales"
    },
]


def normalize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def similarity(user_question, faq_question):
    a = " ".join(normalize(user_question))
    b = " ".join(normalize(faq_question))

    if not a or not b:
        return 0

    # Similarity of complete questions
    sequence_score = SequenceMatcher(None, a, b).ratio()

    # Similarity based on shared words
    stopwords = {
        "what", "is", "are", "the", "a", "an", "do",
        "you", "your", "i", "how", "can", "we", "our",
        "to", "and", "for", "of", "my", "does", "please",
        "me", "tell", "about", "could", "would"
    }

    wa = set(normalize(a)) - stopwords
    wb = set(normalize(b)) - stopwords

    overlap = len(wa & wb) / max(len(wa | wb), 1)

    # Blend the two scores
    return 0.65 * sequence_score + 0.35 * overlap


def answer_question(message, history, faqs):
    if not message or not message.strip():
        return "Please enter a question.", []

    scored = [
        (similarity(message, faq["question"]), faq)
        for faq in faqs
    ]
    scored.sort(key=lambda item: item[0], reverse=True)

    if scored and scored[0][0] >= 0.42:
        score, faq = scored[0]
        answer = faq["answer"]

        # Suggest related questions
        suggestions = [
            item["question"]
            for _, item in scored[1:4]
        ]
        return answer, suggestions

    return (
        "I couldn't find a reliable answer in our FAQ knowledge base. "
        "Please contact support@example.com for help.",
        [item["question"] for _, item in scored[:3]]
    )


def chat(message, history, faqs, logs):
    answer, suggestions = answer_question(message, history, faqs)

    logs = list(logs or [])
    logs.append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "question": message,
        "answer": answer,
        "feedback": "Not provided"
    })

    return (
        answer,
        logs,
        gr.update(choices=suggestions, value=None)
    )


def add_faq(question, answer, category, faqs):
    if not question.strip() or not answer.strip():
        return faqs, "Please enter both a question and an answer."

    updated = list(faqs or [])
    updated.append({
        "question": question.strip(),
        "answer": answer.strip(),
        "category": category.strip() or "General"
    })

    return updated, f"FAQ added successfully. Total FAQs: {len(updated)}"


def delete_faq(question, faqs):
    updated = [
        item for item in (faqs or [])
        if item["question"] != question
    ]

    if len(updated) == len(faqs or []):
        return updated, "Select a valid FAQ to delete."

    return updated, "FAQ deleted."


def import_csv(file, faqs):
    if file is None:
        return faqs, "Please upload a CSV file."

    try:
        with open(file, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"question", "answer"}

            if not reader.fieldnames or not required.issubset(
                set(reader.fieldnames)
            ):
                return faqs, "CSV needs question and answer columns."

            imported = []
            for row in reader:
                q = (row.get("question") or "").strip()
                a = (row.get("answer") or "").strip()

                if q and a:
                    imported.append({
                        "question": q,
                        "answer": a,
                        "category": (
                            row.get("category") or "General"
                        ).strip()
                    })

        if not imported:
            return faqs, "No valid FAQs found in the file."

        return list(faqs or []) + imported, (
            f"Imported {len(imported)} FAQs."
        )

    except Exception as exc:
        return faqs, f"Could not import CSV: {exc}"


def export_csv(faqs):
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["question", "answer", "category"]
    )
    writer.writeheader()
    writer.writerows(faqs or [])

    return output.getvalue()


def record_feedback(feedback, logs):
    logs = list(logs or [])

    if logs:
        logs[-1]["feedback"] = feedback

    positive = sum(
        item["feedback"] == "Helpful" for item in logs
    )
    negative = sum(
        item["feedback"] == "Not helpful" for item in logs
    )
    unanswered = sum(
        "couldn't find a reliable answer" in item["answer"].lower()
        for item in logs
    )

    return (
        logs,
        f"Feedback recorded: {feedback}. "
        f"Questions: {len(logs)} | Helpful: {positive} | "
        f"Not helpful: {negative} | Unanswered: {unanswered}"
    )


with gr.Blocks(title="Business FAQ Assistant") as demo:
    gr.Markdown(
        """
        # Business FAQ Assistant
        Ask questions, explore suggested FAQs, and manage your
        business knowledge base.
        """
    )

    faq_state = gr.State(INITIAL_FAQS)
    log_state = gr.State([])

    with gr.Tab("Chat"):
        chatbot = gr.Chatbot(height=420, label="Conversation")
        message = gr.Textbox(
            placeholder="Ask about services, payments, refunds...",
            label="Your question"
        )

        with gr.Row():
            send = gr.Button("Send", variant="primary")
            clear = gr.Button("Clear conversation")

        suggestions = gr.Dropdown(
            choices=[item["question"] for item in INITIAL_FAQS],
            label="Suggested questions",
            interactive=True
        )

        feedback = gr.Radio(
            ["Helpful", "Not helpful"],
            label="Was the last answer helpful?"
        )
        feedback_status = gr.Markdown()

    with gr.Tab("Manage FAQs"):
        gr.Markdown(
            "Add new questions and answers to your knowledge base."
        )
        new_question = gr.Textbox(label="FAQ question")
        new_answer = gr.Textbox(label="FAQ answer", lines=3)
        new_category = gr.Textbox(
            label="Category",
            value="General"
        )
        add_button = gr.Button("Add FAQ", variant="primary")
        management_status = gr.Markdown()

        delete_question = gr.Dropdown(
            choices=[item["question"] for item in INITIAL_FAQS],
            label="Choose an FAQ to delete"
        )
        delete_button = gr.Button("Delete selected FAQ")

        gr.Markdown("### Import FAQs from CSV")
        csv_file = gr.File(
            label="Upload CSV",
            file_types=[".csv"],
            type="filepath"
        )
        import_button = gr.Button("Import CSV")
        import_status = gr.Markdown()

        gr.Markdown(
            "CSV columns: question, answer, category. "
            "The category column is optional."
        )
        export_button = gr.Button("Export FAQs to CSV")
        export_file = gr.File(label="Download exported FAQs")

    with gr.Tab("Analytics"):
        analytics_output = gr.Markdown(
            "Ask questions and submit feedback to collect analytics."
        )
        refresh_analytics = gr.Button("Refresh analytics")

    def respond(message, history, faqs, logs):
        answer, logs, suggested = chat(
            message, history, faqs, logs
        )

        history = list(history or [])
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer})

        return (
            history, "", logs,
            gr.update(choices=suggested["choices"], value=None)
        )

    send.click(
        respond,
        inputs=[message, chatbot, faq_state, log_state],
        outputs=[chatbot, message, log_state, suggestions]
    )

    message.submit(
        respond,
        inputs=[message, chatbot, faq_state, log_state],
        outputs=[chatbot, message, log_state, suggestions]
    )

    def ask_suggestion(question, history, faqs, logs):
        if not question:
            return history, "", logs

        answer, logs, _ = chat(question, history, faqs, logs)
        history = list(history or [])
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        return history, "", logs

    suggestions.change(
        ask_suggestion,
        inputs=[suggestions, chatbot, faq_state, log_state],
        outputs=[chatbot, message, log_state]
    )

    clear.click(
        lambda: ([], None, ""),
        outputs=[chatbot, feedback, feedback_status]
    )

    feedback.change(
        record_feedback,
        inputs=[feedback, log_state],
        outputs=[log_state, feedback_status]
    )

    add_button.click(
        add_faq,
        inputs=[new_question, new_answer, new_category, faq_state],
        outputs=[faq_state, management_status]
    ).then(
        lambda faqs: gr.update(
            choices=[item["question"] for item in faqs],
            value=None
        ),
        inputs=[faq_state],
        outputs=[delete_question]
    )

    delete_button.click(
        delete_faq,
        inputs=[delete_question, faq_state],
        outputs=[faq_state, management_status]
    ).then(
        lambda faqs: gr.update(
            choices=[item["question"] for item in faqs],
            value=None
        ),
        inputs=[faq_state],
        outputs=[delete_question]
    )

    import_button.click(
        import_csv,
        inputs=[csv_file, faq_state],
        outputs=[faq_state, import_status]
    ).then(
        lambda faqs: gr.update(
            choices=[item["question"] for item in faqs],
            value=None
        ),
        inputs=[faq_state],
        outputs=[delete_question]
    )

    export_button.click(
        lambda faqs: gr.update(
            value=export_csv(faqs),
            visible=True
        ),
        inputs=[faq_state],
        outputs=[export_file]
    )

    def analytics(logs, faqs):
        logs = logs or []
        helpful = sum(
            x["feedback"] == "Helpful" for x in logs
        )
        unhelpful = sum(
            x["feedback"] == "Not helpful" for x in logs
        )
        unanswered = sum(
            "couldn't find a reliable answer" in x["answer"].lower()
            for x in logs
        )

        return f"""
        ### Usage summary

        - **Total questions:** {len(logs)}
        - **FAQs in knowledge base:** {len(faqs or [])}
        - **Helpful ratings:** {helpful}
        - **Not helpful ratings:** {unhelpful}
        - **Unanswered questions:** {unanswered}
        """

    refresh_analytics.click(
        analytics,
        inputs=[log_state, faq_state],
        outputs=[analytics_output]
    )

if __name__ == "__main__":
    demo.launch()
