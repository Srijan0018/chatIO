
import gradio as gr
import re

# Business FAQ knowledge base
faqs = [
    {
        "question": "What services does your business offer?",
        "answer": "We offer business consulting, digital marketing, and customer support services."
    },
    {
        "question": "What are your business hours?",
        "answer": "Our business hours are Monday to Saturday, 9:00 AM to 6:00 PM."
    },
    {
        "question": "How can I contact customer support?",
        "answer": "You can contact our support team at support@example.com."
    },
    {
        "question": "What payment methods do you accept?",
        "answer": "We accept credit cards, debit cards, UPI, and bank transfers."
    },
    {
        "question": "What is your refund policy?",
        "answer": "Refund requests can be submitted within 7 days of purchase, subject to our refund policy."
    },
    {
        "question": "Do you offer discounts?",
        "answer": "Yes, we offer discounts on selected services. Please contact our sales team for details."
    },
    {
        "question": "How can I purchase your services?",
        "answer": "Please contact our sales team to discuss your requirements and purchase options."
    }
]


def get_words(text):
    # Convert text into lowercase words
    return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))


def chatbot(message, history):
    if not message or not message.strip():
        return "Please enter a question."

    user_words = get_words(message)
    best_score = 0
    best_answer = None

    # Find the FAQ with the most matching words
    for faq in faqs:
        question_words = get_words(faq["question"])
        answer_words = get_words(faq["answer"])

        # Match against both the FAQ question and answer
        searchable_words = question_words | answer_words
        common_words = user_words & searchable_words

        # Ignore very common words
        common_words -= {
            "what", "is", "are", "the", "a", "an", "do",
            "you", "your", "i", "how", "can", "our", "we",
            "to", "and", "for", "of", "my", "does"
        }

        if not common_words:
            continue

        score = len(common_words) / max(len(user_words), 1)

        if score > best_score:
            best_score = score
            best_answer = faq["answer"]

    if best_answer and best_score >= 0.30:
        return best_answer

    return (
        "Sorry, I couldn't find an answer to that question in our FAQ. "
        "Please contact our customer support team for assistance."
    )


demo = gr.ChatInterface(
    fn=chatbot,
    title="Business FAQ Assistant",
    description=(
        "Ask me about our services, business hours, "
        "payments, refunds, and customer support."
    ),
    examples=[
        "What services do you offer?",
        "When are you open?",
        "How can I get a refund?",
        "Which payment methods do you accept?"
    ]
)

if __name__ == "__main__":
    demo.launch()
