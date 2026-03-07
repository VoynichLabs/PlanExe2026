"""
Brainstorm what key "levers" can be pulled to change the outcome of the plan.

The output contains near duplicates, these have to be deduplicated. A few lever names appear twice.
The deduplication is done in the deduplicate_levers.py script.

PROMPT> python -m worker_plan_internal.lever.identify_potential_levers
"""
import json
import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
import uuid
from llama_index.core.llms.llm import LLM
from pydantic import BaseModel, Field, field_validator
from llama_index.core.llms import ChatMessage, MessageRole
from worker_plan_internal.llm_util.llm_executor import LLMExecutor, PipelineStopRequested

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Decomposed schemas (PremortemTask pattern)
# ---------------------------------------------------------------------------

class LeverNarrative(BaseModel):
    """Narrative context for a set of levers — kept separate so small models
    are never asked to produce nested lists and narrative text in one shot."""
    strategic_rationale: str = Field(
        description=(
            "A concise strategic analysis (around 100 words) of the project's core tensions "
            "and trade-offs. This rationale must JUSTIFY why the selected levers are the most "
            "critical levers for decision-making. Explain how the chosen levers navigate the "
            "fundamental conflicts between speed, cost, scope, and quality."
        )
    )
    summary: str = Field(
        description=(
            "Evaluate this set of levers. Are they well picked, well balanced, well thought out? "
            "Point out flaws. Identify ONE critical missing dimension. 100 words."
        )
    )


class LeverItem(BaseModel):
    """A single strategic lever — one LLM call per lever (PremortemTask pattern).
    lever_index is intentionally absent; the program assigns it sequentially."""
    name: str = Field(
        description="Name of this lever as a strategic concept (e.g. 'Material Adaptation Strategy')."
    )
    consequences: str = Field(
        description=(
            "Briefly describe the likely second-order effects or consequences of pulling this lever. "
            "Chain three SPECIFIC effects: "
            "'Immediate: [effect] → Systemic: [impact] → Strategic: [implication]'. "
            "Include measurable outcomes where possible. 30 words."
        )
    )
    options: List[str] = Field(
        description=(
            "Exactly 3 qualitative, self-contained strategic choices. "
            "Each option must be a complete strategic description — NO labels or prefixes "
            "(e.g. no 'Option A:', 'Choice 1:'). "
            "Show a clear progression: conservative → moderate → radical."
        )
    )
    review_lever: str = Field(
        description=(
            "Critique this lever. State the core trade-off it controls "
            "(e.g. 'Controls Speed vs. Quality'). "
            "Then identify one specific weakness: "
            "'Weakness: The options fail to consider [specific factor].'"
        )
    )

    @field_validator('options', mode='before')
    @classmethod
    def parse_options(cls, v):
        """Handle cases where LLMs return options as a stringified JSON array."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return v


# ---------------------------------------------------------------------------
# Legacy schemas preserved for backward-compatible serialisation
# (responses are reconstructed from decomposed calls and stored as
#  DocumentDetails so downstream consumers see the same structure)
# ---------------------------------------------------------------------------

class Lever(BaseModel):
    lever_index: int = Field(
        description="Index of this lever."
    )
    name: str = Field(
        description="Name of this lever."
    )
    consequences: str = Field(
        description=(
            "Briefly describe the likely second-order effects or consequences of pulling this lever "
            "(e.g., 'Choosing a high-risk tech strategy will likely increase talent acquisition "
            "difficulty and require a larger contingency budget.'). 30 words."
        )
    )
    options: list[str] = Field(
        description="2-5 options for this lever."
    )
    review_lever: str = Field(
        description=(
            "Critique this lever. State the core trade-off it controls "
            "(e.g., 'Controls Speed vs. Quality'). "
            "Then, identify one specific weakness in how its options address that trade-off."
        )
    )

    @field_validator('options', mode='before')
    @classmethod
    def parse_options(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return v


class DocumentDetails(BaseModel):
    strategic_rationale: str = Field(
        description=(
            "A concise strategic analysis (around 100 words) of the project's core tensions "
            "and trade-offs. This rationale must JUSTIFY why the selected levers are the most "
            "critical levers for decision-making."
        )
    )
    levers: list[Lever] = Field(
        description="Propose exactly 5 levers."
    )
    summary: str = Field(
        description=(
            "Are these levers well picked? Are they well balanced? Are they well thought out? "
            "Point out flaws. 100 words."
        )
    )


class LeverCleaned(BaseModel):
    """
    The Lever class has some ugly field names that guide the LLM for what to generate.
    Changing them and the LLM can't generate as good results.
    This class has nicer field names for the final output.
    """
    lever_id: str = Field(
        description=(
            "A uuid that identifies this lever. The levers can be deduplicated and preserve "
            "their lever_id without leaving gaps in the numbering."
        )
    )
    name: str = Field(
        description="Name of this lever."
    )
    consequences: str = Field(
        description=(
            "Briefly describe the likely second-order effects or consequences of pulling this lever "
            "(e.g., 'Choosing a high-risk tech strategy will likely increase talent acquisition "
            "difficulty and require a larger contingency budget.'). 30 words."
        )
    )
    options: list[str] = Field(
        description="2-5 options for this lever."
    )
    review: str = Field(
        description=(
            "Critique this lever. State the core trade-off it controls "
            "(e.g., 'Controls Speed vs. Quality'). "
            "Then, identify one specific weakness in how its options address that trade-off."
        )
    )


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

# Used for generating a single LeverItem.
# Part A fix: JSON fenced code block removed from Output Requirements.
# The schema injection via as_structured_llm(LeverItem) handles format.
IDENTIFY_POTENTIAL_LEVERS_SYSTEM_PROMPT = """
You are an expert strategic analyst. Generate ONE strategic lever following these directives:

1. **Output Requirements**
   - You are generating EXACTLY ONE lever per response.
   - Provide exactly 3 qualitative, self-contained strategic choices for the options field.
   - Options must be descriptive phrases — no labels, no prefixes (e.g. not "Option A:").

2. **Lever Quality Standards**
   - Consequences MUST:
     • Chain three SPECIFIC effects: "Immediate: [effect] → Systemic: [impact] → Strategic: [implication]"
     • Include measurable outcomes: "Systemic: 25% faster scaling through..."
     • Explicitly describe trade-offs between core tensions
   - Options MUST:
     • Represent distinct strategic pathways (not just labels)
     • Include at least one unconventional/innovative approach
     • Show clear progression: conservative → moderate → radical
     • NO prefixes (e.g., "Option A:", "Choice 1:")

3. **Strategic Framing**
   - Name levers as strategic concepts (e.g., "Material Adaptation Strategy")
   - Frame options as complete strategic approaches
   - Ensure the lever challenges core project assumptions

4. **Validation Protocols**
   - For `review_lever`:
     • State the trade-off explicitly: "Controls [Tension A] vs. [Tension B]."
     • Identify a specific weakness: "Weakness: The options fail to consider [specific factor]."

5. **Prohibitions**
   - NO prefixes/labels in options (e.g., "Option A:", "Choice 1:")
   - NO generic option labels (e.g., "Optimize X", "Tolerate Y")
   - NO placeholder consequences
   - NO "[specific innovative option]" placeholders
   - NO value sets without clear strategic progression

6. **Option Structure Enforcement**
   - Radical option must include emerging tech/business model
   - Maintain parallel grammatical structure across options
   - Ensure options are self-contained descriptions
"""

# Used for generating LeverNarrative (rationale + summary) after levers are known.
LEVER_NARRATIVE_SYSTEM_PROMPT = """
You are an expert strategic analyst evaluating a set of project levers.

Provide:
1. A concise strategic rationale (~100 words) explaining the core tensions and trade-offs
   the project faces and why the identified levers are the most critical for decision-making.
2. A critical summary (~100 words) evaluating whether the lever set is well-balanced and
   well-thought-out. Identify ONE critical missing dimension and suggest a concrete improvement.
"""


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class IdentifyPotentialLevers:
    system_prompt: Optional[str]
    user_prompt: str
    responses: list[DocumentDetails]
    levers: list[LeverCleaned]
    metadata: dict

    # Number of independent generation rounds ("more" passes)
    LEVERS_PER_ROUND: int = 5

    @classmethod
    def execute(cls, llm_executor: LLMExecutor, user_prompt: str) -> 'IdentifyPotentialLevers':
        if not isinstance(llm_executor, LLMExecutor):
            raise ValueError("Invalid LLMExecutor instance.")
        if not isinstance(user_prompt, str):
            raise ValueError("Invalid user_prompt.")

        lever_system_prompt = IDENTIFY_POTENTIAL_LEVERS_SYSTEM_PROMPT.strip()
        narrative_system_prompt = LEVER_NARRATIVE_SYSTEM_PROMPT.strip()

        levers_per_round = 5
        # Round base prompts — first round uses the real plan text; subsequent
        # rounds request distinct additional levers.
        round_base_prompts = [
            user_prompt,
            user_prompt,
            user_prompt,
        ]

        all_lever_items: list[LeverItem] = []
        all_narratives: list[LeverNarrative] = []
        metadata_list: list[dict] = []

        for round_index, base_prompt in enumerate(round_base_prompts, start=1):
            logger.info(f"Round {round_index}/{len(round_base_prompts)}")

            # ---------------------------------------------------------------
            # Part B: One independent LeverItem call per lever
            # lever_index is NOT asked from the LLM — assigned by code below.
            # ---------------------------------------------------------------
            round_lever_items: list[LeverItem] = []
            seen_names: list[str] = [item.name for item in all_lever_items]

            for lever_i in range(1, levers_per_round + 1):
                logger.info(f"  Lever {lever_i}/{levers_per_round} (round {round_index})")

                avoid_note = ""
                current_seen = seen_names + [item.name for item in round_lever_items]
                if current_seen:
                    avoid_note = (
                        f"\n\nAvoid repeating these lever names already generated: "
                        f"{current_seen}. Pick a clearly different strategic dimension."
                    )

                item_user_content = (
                    f"{base_prompt}"
                    f"\n\nGenerate lever {lever_i} of {levers_per_round} for this project."
                    f"{avoid_note}"
                )

                item_chat = [
                    ChatMessage(role=MessageRole.SYSTEM, content=lever_system_prompt),
                    ChatMessage(role=MessageRole.USER, content=item_user_content),
                ]

                def _make_lever_fn(chat):
                    def execute_function(llm: LLM) -> dict:
                        sllm = llm.as_structured_llm(LeverItem)
                        chat_response = sllm.chat(chat)
                        metadata = dict(llm.metadata)
                        metadata["llm_classname"] = llm.class_name()
                        return {"chat_response": chat_response, "metadata": metadata}
                    return execute_function

                try:
                    result = llm_executor.run(_make_lever_fn(item_chat))
                except PipelineStopRequested:
                    raise
                except Exception as e:
                    logger.error("LLM lever item interaction failed.", exc_info=True)
                    raise ValueError("LLM lever item interaction failed.") from e

                round_lever_items.append(result["chat_response"].raw)
                metadata_list.append(result["metadata"])

            all_lever_items.extend(round_lever_items)

            # ---------------------------------------------------------------
            # Part B: One LeverNarrative call per round (after levers known)
            # ---------------------------------------------------------------
            lever_names_str = ", ".join(f'"{item.name}"' for item in round_lever_items)
            narrative_user_content = (
                f"{base_prompt}"
                f"\n\nThe levers identified for this round are: {lever_names_str}. "
                f"Provide strategic rationale and evaluation."
            )

            narrative_chat = [
                ChatMessage(role=MessageRole.SYSTEM, content=narrative_system_prompt),
                ChatMessage(role=MessageRole.USER, content=narrative_user_content),
            ]

            def _make_narrative_fn(chat):
                def execute_function(llm: LLM) -> dict:
                    sllm = llm.as_structured_llm(LeverNarrative)
                    chat_response = sllm.chat(chat)
                    metadata = dict(llm.metadata)
                    metadata["llm_classname"] = llm.class_name()
                    return {"chat_response": chat_response, "metadata": metadata}
                return execute_function

            try:
                narrative_result = llm_executor.run(_make_narrative_fn(narrative_chat))
            except PipelineStopRequested:
                raise
            except Exception as e:
                logger.error("LLM lever narrative interaction failed.", exc_info=True)
                raise ValueError("LLM lever narrative interaction failed.") from e

            all_narratives.append(narrative_result["chat_response"].raw)
            metadata_list.append(narrative_result["metadata"])

        # -------------------------------------------------------------------
        # Reconstruct DocumentDetails per round for backward-compatible
        # serialisation (downstream consumers see the same structure).
        # -------------------------------------------------------------------
        responses: list[DocumentDetails] = []
        for round_idx, narrative in enumerate(all_narratives):
            start = round_idx * levers_per_round
            round_items = all_lever_items[start: start + levers_per_round]
            lever_list = [
                Lever(
                    lever_index=i + 1,
                    name=item.name,
                    consequences=item.consequences,
                    options=item.options,
                    review_lever=item.review_lever,
                )
                for i, item in enumerate(round_items)
            ]
            doc = DocumentDetails(
                strategic_rationale=narrative.strategic_rationale,
                levers=lever_list,
                summary=narrative.summary,
            )
            responses.append(doc)

        # -------------------------------------------------------------------
        # Flatten all lever items and build LeverCleaned list.
        # lever_index is assigned sequentially by code — not by the LLM.
        # -------------------------------------------------------------------
        levers_cleaned: list[LeverCleaned] = []
        for item in all_lever_items:
            lever_cleaned = LeverCleaned(
                lever_id=str(uuid.uuid4()),
                name=item.name,
                consequences=item.consequences,
                options=item.options,
                review=item.review_lever,
            )
            levers_cleaned.append(lever_cleaned)

        metadata: dict = {}
        for metadata_index, metadata_item in enumerate(metadata_list, start=1):
            metadata[f"metadata_{metadata_index}"] = metadata_item

        return IdentifyPotentialLevers(
            system_prompt=lever_system_prompt,
            user_prompt=user_prompt,
            responses=responses,
            levers=levers_cleaned,
            metadata=metadata,
        )

    def to_dict(
        self,
        include_responses=True,
        include_cleaned_levers=True,
        include_metadata=True,
        include_system_prompt=True,
        include_user_prompt=True,
    ) -> dict:
        d = {}
        if include_responses:
            d["responses"] = [response.model_dump() for response in self.responses]
        if include_cleaned_levers:
            d['levers'] = [lever.model_dump() for lever in self.levers]
        if include_metadata:
            d['metadata'] = self.metadata
        if include_system_prompt:
            d['system_prompt'] = self.system_prompt
        if include_user_prompt:
            d['user_prompt'] = self.user_prompt
        return d

    def save_raw(self, file_path: str) -> None:
        Path(file_path).write_text(json.dumps(self.to_dict(), indent=2))

    def lever_item_list(self) -> list[dict]:
        """Return a list of dictionaries, each representing a lever."""
        return [lever.model_dump() for lever in self.levers]

    def save_clean(self, file_path: str) -> None:
        levers_dict = self.lever_item_list()
        Path(file_path).write_text(json.dumps(levers_dict, indent=2))


if __name__ == "__main__":
    from worker_plan_internal.llm_util.llm_executor import LLMModelFromName
    from worker_plan_internal.prompt.prompt_catalog import PromptCatalog

    logging.basicConfig(level=logging.DEBUG)

    prompt_catalog = PromptCatalog()
    prompt_catalog.load_simple_plan_prompts()

    # prompt_id = "b9afce6c-f98d-4e9d-8525-267a9d153b51"
    # prompt_id = "a6bef08b-c768-4616-bc28-7503244eff02"
    # prompt_id = "19dc0718-3df7-48e3-b06d-e2c664ecc07d"
    prompt_id = "e42eafce-5c8c-4801-b9f1-b8b2a402cd78"
    prompt_item = prompt_catalog.find(prompt_id)
    if not prompt_item:
        raise ValueError("Prompt item not found.")
    query = prompt_item.prompt

    model_names = [
        "ollama-llama3.1",
        # "openrouter-paid-gemini-2.0-flash-001",
        # "openrouter-paid-qwen3-30b-a3b"
    ]
    llm_models = LLMModelFromName.from_names(model_names)
    llm_executor = LLMExecutor(llm_models=llm_models)

    print(f"Query: {query}")
    result = IdentifyPotentialLevers.execute(llm_executor, query)

    print("\nResult:")
    json_response = result.to_dict(include_system_prompt=False, include_user_prompt=False)
    print(json.dumps(json_response, indent=2))

    test_data_filename = f"identify_potential_levers_{prompt_id}.json"
    result.save_clean(Path(test_data_filename))
    print(f"Test data saved to: {test_data_filename!r}")
