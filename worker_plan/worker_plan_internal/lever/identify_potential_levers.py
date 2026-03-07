"""
Brainstorm what key "levers" can be pulled to change the outcome of the plan.

The output contains near duplicates, these have to be deduplicated. A few lever names appear twice.
The deduplication is done in the deduplicate_levers.py script.

PROMPT> python -m worker_plan_internal.lever.identify_potential_levers
"""
import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import uuid
from llama_index.core.llms.llm import LLM
from pydantic import BaseModel, Field, field_validator
from llama_index.core.llms import ChatMessage, MessageRole
from worker_plan_internal.llm_util.llm_executor import LLMExecutor, PipelineStopRequested

logger = logging.getLogger(__name__)

class Lever(BaseModel):
    lever_index: int = Field(
        description="Index of this lever."
    )
    name: str = Field(
        description="Name of this lever."
    )
    consequences: str = Field(
        description="Briefly describe the likely second-order effects or consequences of pulling this lever (e.g., 'Choosing a high-risk tech strategy will likely increase talent acquisition difficulty and require a larger contingency budget.'). 30 words."
    )
    options: list[str] = Field(
        description="2-5 options for this lever."
    )
    review_lever: str = Field(
        description="Critique this lever. State the core trade-off it controls (e.g., 'Controls Speed vs. Quality'). Then, identify one specific weakness in how its options address that trade-off."
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

class DocumentDetails(BaseModel):
    strategic_rationale: str = Field(
        description="A concise strategic analysis (around 100 words) of the project's core tensions and trade-offs. This rationale must JUSTIFY why the selected levers are the most critical levers for decision-making. For example, explain how the chosen levers navigate the fundamental conflicts between speed, cost, scope, and quality."
    )
    levers: list[Lever] = Field(
        description="Propose exactly 5 levers."
    )
    summary: str = Field(
        description="Are these levers well picked? Are they well balanced? Are they well thought out? Point out flaws. 100 words."
    )

class LeverNarrative(BaseModel):
    """Minimal per-lever schema. lever_index is assigned by code."""
    name: str = Field(description="A strategic concept name for this lever (e.g. 'Material Adaptation Strategy').")
    consequences: str = Field(description="Chain three specific effects: 'Immediate: [effect] → Systemic: [impact] → Strategic: [implication]'.")
    options: list[str] = Field(description="Exactly 3 qualitative strategic choices: conservative, moderate, and radical/innovative.")
    review_lever: str = Field(description="State the trade-off explicitly and identify one specific weakness.")

class DocumentNarrative(BaseModel):
    """Overall framing for the lever set."""
    strategic_rationale: str = Field(description="Why these levers matter strategically for the project.")
    summary: str = Field(description="Identify ONE critical missing dimension and prescribe a concrete addition.")

class LeverCleaned(BaseModel):
    """
    The Lever class has some ugly field names, that guide the LLM for what to generate. Changing them and the LLM can't generate as good results.
    This class has nicer field names for the final output.
    """
    lever_id: str = Field(
        description="A uuid that identifies this lever. The levers can be deduplicated and preserve their lever_id without leaving gaps in the numbering."
    )
    name: str = Field(
        description="Name of this lever."
    )
    consequences: str = Field(
        description="Briefly describe the likely second-order effects or consequences of pulling this lever (e.g., 'Choosing a high-risk tech strategy will likely increase talent acquisition difficulty and require a larger contingency budget.'). 30 words."
    )
    options: list[str] = Field(
        description="2-5 options for this lever."
    )
    review: str = Field(
        description="Critique this lever. State the core trade-off it controls (e.g., 'Controls Speed vs. Quality'). Then, identify one specific weakness in how its options address that trade-off."
    )

IDENTIFY_POTENTIAL_LEVERS_SYSTEM_PROMPT = """
You are an expert strategic analyst. Generate solution space parameters following these directives:

1. **Output Requirements**
   - You must generate EXACTLY 5 levers per response. Do not generate more or fewer than 5 levers.
   - Each lever's `options` field must contain exactly 3 qualitative strategic choices as plain strings.

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
   - Ensure levers challenge core project assumptions

4. **Validation Protocols**
   - For `review_lever`:
     • State the trade-off explicitly: "Controls [Tension A] vs. [Tension B]."
     • Identify a specific weakness: "Weakness: The options fail to consider [specific factor]."
   - For `summary`:
     • Identify ONE critical missing dimension
     • Prescribe CONCRETE addition: "Add '[full strategic option]' to [lever]"

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

@dataclass
class IdentifyPotentialLevers:
    system_prompt: Optional[str]
    user_prompt: str
    responses: list[DocumentDetails]
    levers: list[LeverCleaned]
    metadata: dict

    @classmethod
    def execute(cls, llm_executor: LLMExecutor, user_prompt: str) -> 'IdentifyPotentialLevers':
        if not isinstance(llm_executor, LLMExecutor):
            raise ValueError("Invalid LLMExecutor instance.")
        if not isinstance(user_prompt, str):
            raise ValueError("Invalid user_prompt.")
        
        system_prompt = IDENTIFY_POTENTIAL_LEVERS_SYSTEM_PROMPT.strip()

        # 3 independent rounds; each decomposed into per-lever calls for small-model compatibility.
        # Round prompts are self-contained (no accumulated history) so small models see a clean context.
        round_user_prompts = [
            user_prompt,
            (
                f"{user_prompt}\n\n"
                "Generate a second set of 5 levers that are thematically different from the first set."
            ),
            (
                f"{user_prompt}\n\n"
                "Generate a third set of 5 levers that cover different strategic dimensions from the previous sets."
            ),
        ]

        responses: list[DocumentDetails] = []
        metadata_list: list[dict] = []

        for round_index, round_user_prompt in enumerate(round_user_prompts, start=1):
            logger.info(f"Processing round {round_index} of {len(round_user_prompts)}")

            lever_narratives: list[LeverNarrative] = []
            lever_metadata_entries: list[dict] = []

            # --- Per-lever calls (5 per round) ---
            for lever_pos in range(1, 6):
                logger.info(f"  Round {round_index}: generating lever {lever_pos} of 5")

                lever_chat_messages = [
                    ChatMessage(
                        role=MessageRole.SYSTEM,
                        content=system_prompt,
                    ),
                    ChatMessage(
                        role=MessageRole.USER,
                        content=round_user_prompt,
                    ),
                    ChatMessage(
                        role=MessageRole.USER,
                        content=(
                            f"Generate lever {lever_pos} of 5. "
                            "Provide ONE specific strategic lever for this project. "
                            "Name it as a strategic concept. "
                            "Give exactly 3 options (conservative, moderate, radical)."
                        ),
                    ),
                ]

                def make_lever_fn(msgs):
                    def execute_lever(llm: LLM) -> dict:
                        sllm = llm.as_structured_llm(LeverNarrative)
                        chat_response = sllm.chat(msgs)
                        metadata = dict(llm.metadata)
                        metadata["llm_classname"] = llm.class_name()
                        return {"chat_response": chat_response, "metadata": metadata}
                    return execute_lever

                lever_narrative: Optional[LeverNarrative] = None
                lever_meta: Optional[dict] = None

                for attempt in range(1, 4):
                    try:
                        result = llm_executor.run(make_lever_fn(lever_chat_messages))
                        lever_narrative = result["chat_response"].raw
                        lever_meta = result["metadata"]
                        break
                    except PipelineStopRequested:
                        raise
                    except Exception as e:
                        logger.warning(f"Round {round_index} lever {lever_pos} attempt {attempt} failed: {e}")
                        if attempt == 3:
                            logger.error(
                                f"Round {round_index} lever {lever_pos} failed after 3 attempts. Skipping."
                            )

                if lever_narrative is not None:
                    lever_narratives.append(lever_narrative)
                    if lever_meta:
                        lever_metadata_entries.append(lever_meta)

            if not lever_narratives:
                logger.warning(f"Round {round_index}: No levers generated. Skipping round.")
                continue

            # --- DocumentNarrative call (once per round) ---
            doc_chat_messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=system_prompt,
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=round_user_prompt,
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=(
                        "Provide the strategic rationale and summary for this set of levers. "
                        "Identify ONE critical missing dimension and prescribe a concrete addition."
                    ),
                ),
            ]

            def execute_doc_narrative(llm: LLM) -> dict:
                sllm = llm.as_structured_llm(DocumentNarrative)
                chat_response = sllm.chat(doc_chat_messages)
                metadata = dict(llm.metadata)
                metadata["llm_classname"] = llm.class_name()
                return {"chat_response": chat_response, "metadata": metadata}

            doc_narrative: DocumentNarrative
            doc_meta: Optional[dict] = None

            try:
                doc_result = llm_executor.run(execute_doc_narrative)
                doc_narrative = doc_result["chat_response"].raw
                doc_meta = doc_result["metadata"]
            except PipelineStopRequested:
                raise
            except Exception as e:
                logger.error(
                    f"Round {round_index} DocumentNarrative failed: {e}", exc_info=True
                )
                doc_narrative = DocumentNarrative(
                    strategic_rationale="Strategic rationale not available.",
                    summary="Summary not available.",
                )

            # Code assigns lever_index sequentially (1-5); LLM never sees or sets it.
            levers_for_round: list[Lever] = []
            for i, ln in enumerate(lever_narratives, start=1):
                lever = Lever(
                    lever_index=i,
                    name=ln.name,
                    consequences=ln.consequences,
                    options=ln.options,
                    review_lever=ln.review_lever,
                )
                levers_for_round.append(lever)

            # Assemble into DocumentDetails for backward-compatible save_raw() output.
            doc_details = DocumentDetails(
                strategic_rationale=doc_narrative.strategic_rationale,
                levers=levers_for_round,
                summary=doc_narrative.summary,
            )
            responses.append(doc_details)

            round_metadata: dict = {}
            for i, m in enumerate(lever_metadata_entries, start=1):
                round_metadata[f"lever_{i}"] = m
            if doc_meta:
                round_metadata["document"] = doc_meta
            metadata_list.append(round_metadata)

        if not responses:
            raise ValueError("No levers generated across all rounds.")

        # Flatten levers from all rounds and clean field names for downstream consumers.
        levers_raw: list[Lever] = []
        for response in responses:
            levers_raw.extend(response.levers)

        levers_cleaned: list[LeverCleaned] = []
        for lever in levers_raw:
            lever_id = str(uuid.uuid4())
            lever_cleaned = LeverCleaned(
                lever_id=lever_id,
                name=lever.name,
                consequences=lever.consequences,
                options=lever.options,
                review=lever.review_lever,
            )
            levers_cleaned.append(lever_cleaned)

        metadata = {}
        for metadata_index, metadata_item in enumerate(metadata_list, start=1):
            metadata[f"metadata_{metadata_index}"] = metadata_item

        return IdentifyPotentialLevers(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            responses=responses,
            levers=levers_cleaned,
            metadata=metadata,
        )

    def to_dict(self, include_responses=True, include_cleaned_levers=True, include_metadata=True, include_system_prompt=True, include_user_prompt=True) -> dict:
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
        """
        Return a list of dictionaries, each representing a lever.
        """
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
