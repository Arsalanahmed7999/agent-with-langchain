"""Development aid: run the study-helper chain once from the terminal.

Usage: uv run python -m learning_companion.study_dev "What is a prompt template?"
"""

import sys

from learning_companion.chain import ConfigError, build_study_chain
from learning_companion.settings import get_settings


def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: python -m learning_companion.study_dev "your question"')
        return 1
    try:
        chain = build_study_chain(get_settings())
    except ConfigError as exc:
        print(exc)
        return 1
    print(chain.invoke({"question": question}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
