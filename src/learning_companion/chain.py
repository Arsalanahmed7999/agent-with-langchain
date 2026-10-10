from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from learning_companion.settings import Settings

SYSTEM_INSTRUCTION = (
    "You are the Learning Companion, a friendly tutor for beginners learning "
    "LangChain and LangGraph. Explain simply and keep answers short."
)


# Most recent prior messages taken from the current request. Nothing is stored.
MAX_HISTORY_MESSAGES = 10

# Order: application instruction, request-provided history, latest user message.
PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=SYSTEM_INSTRUCTION),
        MessagesPlaceholder("history", optional=True),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)


def build_history(messages: list[tuple[str, str]]) -> list:
    """Prior (role, text) pairs -> LangChain messages, newest MAX_HISTORY_MESSAGES.

    Only user and assistant roles with text are kept; system is never accepted.
    """
    kept = [(r, t) for r, t in messages if r in ("user", "assistant") and t.strip()]
    return [
        HumanMessage(content=t) if r == "user" else AIMessage(content=t)
        for r, t in kept[-MAX_HISTORY_MESSAGES:]
    ]


def describe_messages(inputs: dict, prompt: ChatPromptTemplate = PROMPT) -> str:
    """Roles and counts only: never keys, instruction text, or user text."""
    roles = [m.type for m in prompt.format_messages(**inputs)]
    return f"roles={roles} count={len(roles)}"


STUDY_SYSTEM_INSTRUCTION = (
    "You are the study helper in the Learning Companion, for beginners learning "
    "LangChain and LangGraph. Explain the concept asked about in plain, concise "
    "language, with no greeting. Add a small example only where it helps. End "
    "with exactly one small suggested next learning step. You do not research, "
    "browse, or retrieve course data, and your answer may contain mistakes."
)

# Order: study instruction, request-provided history, latest user message.
STUDY_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=STUDY_SYSTEM_INSTRUCTION),
        MessagesPlaceholder("history", optional=True),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)


STUDY_MARKER = "/study"


def select_route(question: str) -> tuple[str, str]:
    """The whole routing rule: a leading /study picks the study helper.

    Returns (route, question). Only the leading marker is removed.
    """
    text = question.lstrip()
    if text.startswith(STUDY_MARKER) and (
        len(text) == len(STUDY_MARKER) or text[len(STUDY_MARKER)].isspace()
    ):
        return "study", text[len(STUDY_MARKER) :].strip()
    return "general", question


class ConfigError(Exception):
    pass


def build_chain(settings: Settings):
    """prompt -> Gemini chat model -> text output."""
    if not settings.gemini_api_key:
        raise ConfigError("GEMINI_API_KEY is not set. Add it to your .env file.")
    if not settings.gemini_model_name:
        raise ConfigError("GEMINI_MODEL_NAME is not set. Add it to your .env file.")
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model_name,
        google_api_key=settings.gemini_api_key,
    )
    return PROMPT | model | StrOutputParser()


def build_study_chain(settings: Settings):
    """study prompt -> Gemini chat model -> text output."""
    if not settings.gemini_api_key:
        raise ConfigError("GEMINI_API_KEY is not set. Add it to your .env file.")
    if not settings.gemini_model_name:
        raise ConfigError("GEMINI_MODEL_NAME is not set. Add it to your .env file.")
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model_name,
        google_api_key=settings.gemini_api_key,
    )
    return STUDY_PROMPT | model | StrOutputParser()


REVIEW_INSTRUCTION = (
    "You review one draft answer from the Learning Companion for beginners. "
    "Rule: the draft must be clear, in plain language, and suitable for a "
    "beginner. For route 'general' it should be a friendly, helpful reply. For "
    "route 'study' it should be a concise explanation, with a small example "
    "where useful, ending with exactly one next learning step. It must not claim "
    "to research, browse, or retrieve data. Decide 'approve' if the draft meets "
    "the rule, otherwise 'improve'. Give one short plain-English reason."
)

IMPROVE_INSTRUCTION = (
    "You rewrite one draft answer from the Learning Companion once, using the "
    "reviewer reason. Keep it plain, short, and suited to a beginner. For "
    "route 'study' keep a concise explanation and end with exactly one next "
    "learning step. Do not add greetings, claim to research or browse, or "
    "mention the review. Return only the rewritten answer."
)

REVIEW_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=REVIEW_INSTRUCTION),
        HumanMessagePromptTemplate.from_template(
            "Route: {route}\n\nDraft answer:\n{draft}"
        ),
    ]
)

IMPROVE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=IMPROVE_INSTRUCTION),
        HumanMessagePromptTemplate.from_template(
            "Route: {route}\n\nDraft answer:\n{draft}\n\nReviewer reason:\n{reason}"
        ),
    ]
)


class ReviewDecision(BaseModel):
    decision: Literal["approve", "improve"]
    reason: str


def _model(settings: Settings) -> ChatGoogleGenerativeAI:
    if not settings.gemini_api_key:
        raise ConfigError("GEMINI_API_KEY is not set. Add it to your .env file.")
    if not settings.gemini_model_name:
        raise ConfigError("GEMINI_MODEL_NAME is not set. Add it to your .env file.")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model_name,
        google_api_key=settings.gemini_api_key,
    )


def build_review_chain(settings: Settings):
    """review prompt -> Gemini (structured ReviewDecision)."""
    return REVIEW_PROMPT | _model(settings).with_structured_output(ReviewDecision)


def build_improve_chain(settings: Settings):
    """improve prompt -> Gemini -> text output."""
    return IMPROVE_PROMPT | _model(settings) | StrOutputParser()
