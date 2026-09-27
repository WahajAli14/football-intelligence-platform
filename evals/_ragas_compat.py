"""
TEMPORARY COMPATIBILITY WORKAROUND - not part of the architecture.

`ragas.llms.base` (ragas==0.4.3) unconditionally imports `ChatVertexAI` from
`langchain_community.chat_models.vertexai`, but that submodule was removed
from recent `langchain-community` releases (the Vertex AI integration moved
to a separate package). This is a known upstream ragas bug, still open as of
2026-09-27: https://github.com/vibrantlabsai/ragas/issues/2745 (and #2753,
#2741, #2995), with an unmerged fix at
https://github.com/vibrantlabsai/ragas/pull/3017.

The class is only used in a static isinstance() check list
(`MULTIPLE_COMPLETION_SUPPORTED`) - we never use Vertex AI, so a stub module
with an inert placeholder class is enough to let `import ragas` succeed.

DELETE this file (and its import in evals/run_eval.py) once ragas ships a
version with the import properly guarded, or once we upgrade past whichever
release fixes #2745.

Import this module before importing anything from `ragas`.
"""

import sys
import types

_MODULE_NAME = "langchain_community.chat_models.vertexai"

if _MODULE_NAME not in sys.modules:
    _stub = types.ModuleType(_MODULE_NAME)

    class ChatVertexAI:  # never instantiated; placeholder for ragas's isinstance() check
        pass

    _stub.ChatVertexAI = ChatVertexAI
    sys.modules[_MODULE_NAME] = _stub
