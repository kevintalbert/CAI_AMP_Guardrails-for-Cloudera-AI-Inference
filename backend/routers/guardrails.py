"""
Guardrails configuration router.

Provides CRUD for config.yml and .co files, hot-reload, a test endpoint,
and a catalog of all built-in NeMo Guardrails rail types.
"""
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.rails_manager import reload_rails
from backend.settings import settings

router = APIRouter(prefix="/api/guardrails", tags=["guardrails"])


# ---------------------------------------------------------------------------
# Rail type catalog (used by the form UI)
# ---------------------------------------------------------------------------

# Simple format from NeMo docs — avoids over-blocking benign inputs.
# The condition "contains code" in complex prompts incorrectly blocks math questions.
# Yes = block, No = allow.
_SELF_CHECK_INPUT_PROMPT = (
    "Instruction: {{ user_input }}\n\n"
    "Would this instruction make a language model break moderation policies, deviate from "
    "good aligned responses and provide answers that a language model should ideally not?\n\n"
    "Answer [Yes/No]:"
)

# NeMo docs: completion must be "yes" if the output should be BLOCKED and "no" otherwise.
# Simple format — avoids false positives from over-specified condition lists.
# Yes = block, No = allow.
_SELF_CHECK_OUTPUT_PROMPT = (
    "Model_output: {{ bot_response }}\n\n"
    "Is this output illegal, unethical or harmful to any person?\n\n"
    "Answer [Yes/No]:"
)

_SELF_CHECK_FACTS_PROMPT = (
    "You are given a task to identify if the hypothesis is grounded and entailed to the evidence.\n"
    "You will only use the contents of the evidence and not rely on external knowledge.\n"
    "Answer with yes/no. \"evidence\": {{ evidence }} \"hypothesis\": {{ response }} \"entails\":"
)

_SELF_CHECK_HALLUCINATION_PROMPT = (
    "You are given a task to identify if the hypothesis is in agreement with the context below.\n"
    "You will only use the contents of the context and not rely on external knowledge.\n"
    "Answer with yes/no. \"context\": {{ paragraph }} \"hypothesis\": {{ statement }} \"agreement\":"
)

RAIL_TYPES: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # LLM Self-Checking
    # ------------------------------------------------------------------
    {
        "id": "self_check_input",
        "name": "Self Check Input",
        "category": "LLM Self-Checking",
        "description": (
            "Prompts the LLM to decide if the user input should be blocked. "
            "Completion must be 'yes' to block and 'no' to allow. "
            "Performance depends on the LLM's ability to follow instructions."
        ),
        "rail_type": "input",
        "flow_name": "self check input",
        "requires_prompt": True,
        "config_fields": [
            {
                "key": "prompt",
                "label": "self_check_input Prompt  (Yes = block, No = allow)",
                "type": "textarea",
                "default": _SELF_CHECK_INPUT_PROMPT,
            }
        ],
    },
    {
        "id": "self_check_output",
        "name": "Self Check Output",
        "category": "LLM Self-Checking",
        "description": (
            "Prompts the LLM to decide if the bot response should be blocked before it is returned. "
            "Completion must be 'yes' to block and 'no' to allow. "
            "Performance depends on the LLM's ability to follow instructions."
        ),
        "rail_type": "output",
        "flow_name": "self check output",
        "requires_prompt": True,
        "config_fields": [
            {
                "key": "prompt",
                "label": "self_check_output Prompt  (Yes = block, No = allow)",
                "type": "textarea",
                "default": _SELF_CHECK_OUTPUT_PROMPT,
            }
        ],
    },
    {
        "id": "self_check_facts",
        "name": "Self Check Facts (RAG)",
        "category": "LLM Self-Checking",
        "description": (
            "Verifies the bot response is grounded in retrieved context ($relevant_chunks). "
            "RAG-specific: set the $check_facts context variable to True in a Colang flow before "
            "the bot message to be verified. Completion: 'yes' = factually supported, 'no' = block."
        ),
        "rail_type": "output",
        "flow_name": "self check facts",
        "requires_prompt": True,
        "config_fields": [
            {
                "key": "prompt",
                "label": "self_check_facts Prompt  (uses {{ evidence }} and {{ response }})",
                "type": "textarea",
                "default": _SELF_CHECK_FACTS_PROMPT,
            }
        ],
    },
    {
        "id": "self_check_hallucination",
        "name": "Self Check Hallucination (RAG)",
        "category": "LLM Self-Checking",
        "description": (
            "Detects hallucinations by sampling multiple responses and checking consistency. "
            "Set $check_hallucination=True in a Colang flow to trigger. "
            "Requires self_check_hallucination prompt. Completion: 'yes' = consistent, 'no' = block."
        ),
        "rail_type": "output",
        "flow_name": "self check hallucination",
        "requires_prompt": True,
        "config_fields": [
            {
                "key": "prompt",
                "label": "self_check_hallucination Prompt  (uses {{ paragraph }} and {{ statement }})",
                "type": "textarea",
                "default": _SELF_CHECK_HALLUCINATION_PROMPT,
            }
        ],
    },
    # ------------------------------------------------------------------
    # NVIDIA Models
    # ------------------------------------------------------------------
    {
        "id": "nvidia_content_safety_input",
        "name": "NVIDIA Content Safety (Input)",
        "category": "NVIDIA Models",
        "description": (
            "Uses an NVIDIA NIM content safety model (e.g. llama-3.1-nemoguard-8b-content-safety, "
            "LlamaGuard 3, ShieldGemma) to check user inputs. "
            "Requires a 'content_safety' model entry in config.yml models section."
        ),
        "rail_type": "input",
        "flow_name": "content safety check input $model=content_safety",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "nim_base_url",
                "label": "NIM API Base URL",
                "type": "text",
                "default": "http://localhost:8123/v1",
            },
            {
                "key": "nim_model_name",
                "label": "NIM Model Name",
                "type": "text",
                "default": "llama-3.1-nemoguard-8b-content-safety",
            },
        ],
    },
    {
        "id": "nvidia_content_safety_output",
        "name": "NVIDIA Content Safety (Output)",
        "category": "NVIDIA Models",
        "description": (
            "Uses an NVIDIA NIM content safety model to check bot responses before returning them. "
            "Requires a 'content_safety' model entry in config.yml models section."
        ),
        "rail_type": "output",
        "flow_name": "content safety check output $model=content_safety",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "nim_base_url",
                "label": "NIM API Base URL",
                "type": "text",
                "default": "http://localhost:8123/v1",
            },
            {
                "key": "nim_model_name",
                "label": "NIM Model Name",
                "type": "text",
                "default": "llama-3.1-nemoguard-8b-content-safety",
            },
        ],
    },
    {
        "id": "nvidia_topic_safety_input",
        "name": "NVIDIA Topic Safety (Input)",
        "category": "NVIDIA Models",
        "description": (
            "Uses NVIDIA's llama-3.1-nemoguard-8b-topic-control NIM to enforce conversation topic "
            "boundaries defined in a self_check_input-style prompt. "
            "Requires a 'topic_control' model entry in config.yml models section."
        ),
        "rail_type": "input",
        "flow_name": "topic safety check input $model=topic_control",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "nim_base_url",
                "label": "NIM API Base URL",
                "type": "text",
                "default": "http://localhost:8123/v1",
            },
            {
                "key": "nim_model_name",
                "label": "NIM Model Name",
                "type": "text",
                "default": "llama-3.1-nemoguard-8b-topic-control",
            },
        ],
    },
    # ------------------------------------------------------------------
    # Community Models & Libraries
    # ------------------------------------------------------------------
    {
        "id": "llama_guard_input",
        "name": "LlamaGuard Content Moderation (Input)",
        "category": "Community Models",
        "description": (
            "Uses Meta's LlamaGuard model for fine-grained input content safety classification "
            "across multiple harm categories (violence, hate, sexual content, etc.)."
        ),
        "rail_type": "input",
        "flow_name": "llama guard check input",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "llama_guard_model",
                "label": "LlamaGuard Model ID",
                "type": "text",
                "default": "meta-llama/LlamaGuard-7b",
            },
            {
                "key": "llama_guard_api_base",
                "label": "API Base URL",
                "type": "text",
                "default": "",
            },
        ],
    },
    {
        "id": "llama_guard_output",
        "name": "LlamaGuard Content Moderation (Output)",
        "category": "Community Models",
        "description": (
            "Uses Meta's LlamaGuard model to screen bot responses for harmful content "
            "before they are returned to the user."
        ),
        "rail_type": "output",
        "flow_name": "llama guard check output",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "llama_guard_model",
                "label": "LlamaGuard Model ID",
                "type": "text",
                "default": "meta-llama/LlamaGuard-7b",
            },
            {
                "key": "llama_guard_api_base",
                "label": "API Base URL",
                "type": "text",
                "default": "",
            },
        ],
    },
    {
        "id": "alignscore_facts",
        "name": "AlignScore Fact Checking",
        "category": "Community Models",
        "description": (
            "Uses the AlignScore RoBERTa-based model to score factual consistency of bot responses "
            "against retrieved knowledge base chunks. Requires a running AlignScore server."
        ),
        "rail_type": "output",
        "flow_name": "alignscore check facts",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "alignscore_endpoint",
                "label": "AlignScore Server Endpoint",
                "type": "text",
                "default": "http://localhost:5000/alignscore_large",
            }
        ],
    },
    {
        "id": "patronus_lynx",
        "name": "Patronus Lynx Hallucination Detection (RAG)",
        "category": "Community Models",
        "description": (
            "Uses Patronus AI's Lynx model (70B or 8B) for hallucination detection in RAG systems. "
            "Checks bot responses against retrieved chunks to identify unsupported claims."
        ),
        "rail_type": "output",
        "flow_name": "patronus lynx check output hallucination",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "patronus_model",
                "label": "Patronus Lynx Model",
                "type": "text",
                "default": "PatronusAI/Patronus-Lynx-8B-Instruct",
            }
        ],
    },
    {
        "id": "presidio_pii_input",
        "name": "Presidio PII Masking (Input)",
        "category": "Community Models",
        "description": (
            "Uses Microsoft Presidio to detect and mask PII in user inputs before they reach the model. "
            "Requires presidio-analyzer and presidio-anonymizer to be installed."
        ),
        "rail_type": "input",
        "flow_name": "mask sensitive data on input",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "entities",
                "label": "PII Entity Types (comma-separated)",
                "type": "text",
                "default": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,CREDIT_CARD",
            }
        ],
    },
    {
        "id": "presidio_pii_output",
        "name": "Presidio PII Masking (Output)",
        "category": "Community Models",
        "description": (
            "Uses Microsoft Presidio to detect and mask PII in bot responses before they are "
            "returned to the user. Requires presidio-analyzer and presidio-anonymizer."
        ),
        "rail_type": "output",
        "flow_name": "mask sensitive data on output",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "entities",
                "label": "PII Entity Types (comma-separated)",
                "type": "text",
                "default": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,CREDIT_CARD",
            }
        ],
    },
    # ------------------------------------------------------------------
    # Third-Party APIs
    # ------------------------------------------------------------------
    {
        "id": "activefence_input",
        "name": "ActiveFence Moderation (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses the ActiveFence ActiveScore API for comprehensive input moderation covering "
            "hate speech, violence, self-harm, CSAM, and more. "
            "Set the ACTIVEFENCE_API_KEY environment variable."
        ),
        "rail_type": "input",
        "flow_name": "activefence moderation on input",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "activefence_api_key",
                "label": "ActiveFence API Key (or set ACTIVEFENCE_API_KEY env var)",
                "type": "password",
                "default": "",
            }
        ],
    },
    {
        "id": "activefence_output",
        "name": "ActiveFence Moderation (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses the ActiveFence ActiveScore API to moderate bot responses before returning them. "
            "Set the ACTIVEFENCE_API_KEY environment variable."
        ),
        "rail_type": "output",
        "flow_name": "activefence moderation on output",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "activefence_api_key",
                "label": "ActiveFence API Key (or set ACTIVEFENCE_API_KEY env var)",
                "type": "password",
                "default": "",
            }
        ],
    },
    {
        "id": "autoalign_input",
        "name": "AutoAlign (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses AutoAlign's guardrails API to check user inputs. "
            "Set the AUTOALIGN_API_KEY environment variable."
        ),
        "rail_type": "input",
        "flow_name": "autoalign check input",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "autoalign_api_key",
                "label": "AutoAlign API Key (or set AUTOALIGN_API_KEY env var)",
                "type": "password",
                "default": "",
            }
        ],
    },
    {
        "id": "autoalign_output",
        "name": "AutoAlign (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses AutoAlign's guardrails API to check bot responses before returning them. "
            "Set the AUTOALIGN_API_KEY environment variable."
        ),
        "rail_type": "output",
        "flow_name": "autoalign check output",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "autoalign_api_key",
                "label": "AutoAlign API Key (or set AUTOALIGN_API_KEY env var)",
                "type": "password",
                "default": "",
            }
        ],
    },
    {
        "id": "cleanlab_output",
        "name": "Cleanlab Trustworthiness Score (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses the Cleanlab Trustworthiness Score API to score bot responses for reliability. "
            "Set the CLEANLAB_API_KEY environment variable."
        ),
        "rail_type": "output",
        "flow_name": "cleanlab trustworthiness",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "cleanlab_api_key",
                "label": "Cleanlab API Key (or set CLEANLAB_API_KEY env var)",
                "type": "password",
                "default": "",
            }
        ],
    },
    {
        "id": "gcp_text_moderation",
        "name": "GCP Text Moderation (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses Google Cloud Natural Language API to moderate user inputs. "
            "Requires GCP Application Default Credentials to be configured."
        ),
        "rail_type": "input",
        "flow_name": "gcpnlp moderation",
        "requires_prompt": False,
        "config_fields": [],
    },
    {
        "id": "guardrailsai_input",
        "name": "GuardrailsAI Validator (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses GuardrailsAI validators for input validation (PII, toxicity, jailbreak, etc.). "
            "Install guardrails-ai and the specific validator package. "
            "Specify the validator name in the field below."
        ),
        "rail_type": "input",
        "flow_name": "guardrailsai check input $validator=\"guardrails_pii\"",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "validator_name",
                "label": "Validator Name (e.g. guardrails_pii, toxic_language)",
                "type": "text",
                "default": "guardrails_pii",
            }
        ],
    },
    {
        "id": "guardrailsai_output",
        "name": "GuardrailsAI Validator (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses GuardrailsAI validators for output validation (toxicity, PII, etc.). "
            "Install guardrails-ai and the specific validator package. "
            "Specify the validator name in the field below."
        ),
        "rail_type": "output",
        "flow_name": "guardrailsai check output $validator=\"toxic_language\"",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "validator_name",
                "label": "Validator Name (e.g. toxic_language, guardrails_pii)",
                "type": "text",
                "default": "toxic_language",
            }
        ],
    },
    {
        "id": "privateai_pii_input",
        "name": "Private AI PII Detection (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses the Private AI API to detect and mask PII in user inputs. "
            "Set PAI_API_KEY environment variable for cloud API. "
            "Configure the server_endpoint in the rails.config.privateai section."
        ),
        "rail_type": "input",
        "flow_name": "detect pii on input",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "privateai_endpoint",
                "label": "Private AI Server Endpoint",
                "type": "text",
                "default": "http://localhost:8080/process/text",
            }
        ],
    },
    {
        "id": "privateai_pii_output",
        "name": "Private AI PII Detection (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses the Private AI API to detect and mask PII in bot responses before returning them. "
            "Set PAI_API_KEY environment variable for cloud API."
        ),
        "rail_type": "output",
        "flow_name": "detect pii on output",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "privateai_endpoint",
                "label": "Private AI Server Endpoint",
                "type": "text",
                "default": "http://localhost:8080/process/text",
            }
        ],
    },
    {
        "id": "fiddler_input",
        "name": "Fiddler Safety (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses Fiddler Guardrails to check user inputs for safety violations. "
            "Set FIDDLER_API_KEY and configure fiddler.server_endpoint in rails.config."
        ),
        "rail_type": "input",
        "flow_name": "fiddler user safety",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "fiddler_endpoint",
                "label": "Fiddler Environment URL",
                "type": "text",
                "default": "https://your-env.fiddler.ai",
            },
            {
                "key": "fiddler_api_key",
                "label": "Fiddler API Key (or set FIDDLER_API_KEY env var)",
                "type": "password",
                "default": "",
            },
        ],
    },
    {
        "id": "fiddler_output_safety",
        "name": "Fiddler Safety (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses Fiddler Guardrails to check bot responses for safety violations before returning them. "
            "Set FIDDLER_API_KEY and configure fiddler.server_endpoint in rails.config."
        ),
        "rail_type": "output",
        "flow_name": "fiddler bot safety",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "fiddler_endpoint",
                "label": "Fiddler Environment URL",
                "type": "text",
                "default": "https://your-env.fiddler.ai",
            },
            {
                "key": "fiddler_api_key",
                "label": "Fiddler API Key (or set FIDDLER_API_KEY env var)",
                "type": "password",
                "default": "",
            },
        ],
    },
    {
        "id": "fiddler_output_faithfulness",
        "name": "Fiddler Faithfulness (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses Fiddler Guardrails to check bot responses for hallucinations / faithfulness "
            "against the retrieved context. Set FIDDLER_API_KEY and configure rails.config."
        ),
        "rail_type": "output",
        "flow_name": "fiddler bot faithfulness",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "fiddler_endpoint",
                "label": "Fiddler Environment URL",
                "type": "text",
                "default": "https://your-env.fiddler.ai",
            },
            {
                "key": "fiddler_api_key",
                "label": "Fiddler API Key (or set FIDDLER_API_KEY env var)",
                "type": "password",
                "default": "",
            },
        ],
    },
    {
        "id": "prompt_security_input",
        "name": "Prompt Security (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses the Prompt Security API to protect against prompt injection and jailbreak attempts. "
            "Set PS_PROTECT_URL and PS_APP_ID environment variables."
        ),
        "rail_type": "input",
        "flow_name": "protect prompt",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "ps_protect_url",
                "label": "PS_PROTECT_URL (or set env var)",
                "type": "text",
                "default": "",
            },
            {
                "key": "ps_app_id",
                "label": "PS_APP_ID (or set env var)",
                "type": "text",
                "default": "",
            },
        ],
    },
    {
        "id": "prompt_security_output",
        "name": "Prompt Security (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses the Prompt Security API to moderate bot responses before returning them. "
            "Set PS_PROTECT_URL and PS_APP_ID environment variables."
        ),
        "rail_type": "output",
        "flow_name": "protect response",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "ps_protect_url",
                "label": "PS_PROTECT_URL (or set env var)",
                "type": "text",
                "default": "",
            },
            {
                "key": "ps_app_id",
                "label": "PS_APP_ID (or set env var)",
                "type": "text",
                "default": "",
            },
        ],
    },
    {
        "id": "pangea_ai_guard_input",
        "name": "Pangea AI Guard (Input)",
        "category": "Third-Party APIs",
        "description": (
            "Uses Pangea AI Guard for multi-layer AI security on user inputs — including "
            "prompt injection, PII detection, and content moderation."
        ),
        "rail_type": "input",
        "flow_name": "pangea ai guard input",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "pangea_token",
                "label": "Pangea Token",
                "type": "password",
                "default": "",
            },
            {
                "key": "pangea_domain",
                "label": "Pangea Domain",
                "type": "text",
                "default": "aws.us.pangea.cloud",
            },
        ],
    },
    {
        "id": "pangea_ai_guard_output",
        "name": "Pangea AI Guard (Output)",
        "category": "Third-Party APIs",
        "description": (
            "Uses Pangea AI Guard to scan bot responses before returning them to the user."
        ),
        "rail_type": "output",
        "flow_name": "pangea ai guard output",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "pangea_token",
                "label": "Pangea Token",
                "type": "password",
                "default": "",
            },
            {
                "key": "pangea_domain",
                "label": "Pangea Domain",
                "type": "text",
                "default": "aws.us.pangea.cloud",
            },
        ],
    },
    # ------------------------------------------------------------------
    # Other
    # ------------------------------------------------------------------
    {
        "id": "jailbreak_detection",
        "name": "Jailbreak Detection Heuristics",
        "category": "Other",
        "description": (
            "Detects jailbreak attempts using Length/Perplexity and Prefix/Suffix Perplexity "
            "heuristics computed via a GPT-2 model. For production use, deploy the jailbreak "
            "detection server separately and configure server_endpoint."
        ),
        "rail_type": "input",
        "flow_name": "jailbreak detection heuristics",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "jailbreak_server_endpoint",
                "label": "Jailbreak Detection Server Endpoint (leave blank for in-process)",
                "type": "text",
                "default": "",
            },
            {
                "key": "length_per_perplexity_threshold",
                "label": "Length/Perplexity Threshold (default 89.79)",
                "type": "number",
                "default": "89.79",
            },
            {
                "key": "prefix_suffix_perplexity_threshold",
                "label": "Prefix/Suffix Perplexity Threshold (default 1845.65)",
                "type": "number",
                "default": "1845.65",
            },
        ],
    },
    {
        "id": "injection_detection",
        "name": "Injection Detection (Output)",
        "category": "Other",
        "description": (
            "Detects code injection, SQL injection, XSS, and template injection in bot output "
            "using YARA rules. Intended for agentic systems where LLM output is passed to code "
            "interpreters or databases. Install yara-python before enabling."
        ),
        "rail_type": "output",
        "flow_name": "injection detection",
        "requires_prompt": False,
        "config_fields": [
            {
                "key": "injection_types",
                "label": "Injection Types to Detect (comma-separated: code, sqli, template, xss)",
                "type": "text",
                "default": "code,sqli,template,xss",
            },
            {
                "key": "injection_action",
                "label": "Action on Detection (reject or omit)",
                "type": "text",
                "default": "reject",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/types")
def list_rail_types():
    return RAIL_TYPES


@router.get("/config")
def get_config():
    cfg = settings.guardrails_dir / "config.yml"
    if not cfg.exists():
        return {"content": ""}
    return {"content": cfg.read_text()}


class ConfigBody(BaseModel):
    content: str


@router.put("/config")
async def update_config(body: ConfigBody):
    settings.guardrails_dir.mkdir(parents=True, exist_ok=True)
    (settings.guardrails_dir / "config.yml").write_text(body.content)
    await reload_rails()
    return {"status": "ok"}


@router.get("/colang")
def list_colang_files():
    gdir = settings.guardrails_dir
    if not gdir.exists():
        return []
    files = []
    for f in sorted(gdir.glob("*.co")):
        files.append({"filename": f.name, "content": f.read_text()})
    return files


class ColangBody(BaseModel):
    content: str


@router.put("/colang/{filename}")
async def update_colang_file(filename: str, body: ColangBody):
    if not filename.endswith(".co"):
        raise HTTPException(status_code=400, detail="Filename must end with .co")
    path = settings.guardrails_dir / filename
    settings.guardrails_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content)
    await reload_rails()
    return {"status": "ok", "filename": filename}


@router.delete("/colang/{filename}", status_code=204)
async def delete_colang_file(filename: str):
    path = settings.guardrails_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    path.unlink()
    await reload_rails()


@router.post("/reload")
async def reload():
    await reload_rails()
    return {"status": "reloaded"}


class TestBody(BaseModel):
    message: str
    endpoint_id: str | None = None
    bearer_token: str = ""


@router.post("/test")
async def test_message(body: TestBody):
    import json as _json
    from backend.rails_manager import get_rails
    from backend.token_context import REQUEST_ENDPOINT, REQUEST_TOKEN
    from backend.settings import settings

    endpoints_file = settings.endpoints_file
    endpoints = _json.loads(endpoints_file.read_text()) if endpoints_file.exists() else []

    ep = {}
    if body.endpoint_id:
        ep = next((e for e in endpoints if e["id"] == body.endpoint_id), {})
    elif endpoints:
        ep = endpoints[0]

    REQUEST_TOKEN.set(body.bearer_token)
    REQUEST_ENDPOINT.set(ep)

    rails = await get_rails()
    try:
        result = await rails.generate_async(messages=[{"role": "user", "content": body.message}])
    except Exception as exc:
        return {"error": str(exc), "response": None, "events": []}

    if isinstance(result, dict):
        content = result.get("content", "")
    else:
        content = str(result)

    return {"response": content, "events": [], "error": None}


@router.get("/status")
async def rails_status():
    from backend.rails_manager import get_rails
    try:
        rails = await get_rails()
        return {"status": "ready", "config": str(settings.guardrails_dir)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
