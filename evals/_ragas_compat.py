"""
Compatibility shim for ragas 0.4.x.

`ragas.llms.base` unconditionally imports `ChatVertexAI` from
`langchain_community.chat_models.vertexai`, but that submodule was removed
from recent `langchain-community` releases (the Vertex AI integration moved
to a separate package). The class is only used in a static isinstance()
check list (`MULTIPLE_COMPLETION_SUPPORTED`) - we never use Vertex AI, so a
stub module with an inert placeholder class is enough to let `import ragas`
succeed.

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
