"""This is the new, simpler and more evaluatable implementation of _massi_ - the multi-agent system for metadata construction.

# The core idea

Keep the things super simple.

I have the following formalisation of _metadata construction_:

1. It is a composite task `M`.
2. It consists of two stages: _`C`: tempate creation_ and _`P`: template population_.
3. The template creation receives two inputs: `d`: dataset overview and `S`: metadata schema, and produces a `t`: metadata template.
4. The template population receives one input: `t`: metadata template, and produces a `m`: metadata instance.
5. So together, `M = P . C`

## The experiments

Three treatments: 4 baselines, and one treatment multi-agent system with two variants.
We further ablate the treatment variants on: agent presence, underlying LLM models, `tool_usage_limit` values.

---

### Baselines

#### Baseline 1: `BL-1`

Single LLM for the whole `M` task.
LLM is seen as a powerful `SuperArchitect` - it can do the whole thing.

#### Baseline 2: `BL-2`

Single LLM per task stage: `C` and `P`.
- For `C`, we are making the `Architect` a bit more humble, by asking it to produce placeholders for values it can not directly identify but considers necessary for the metadata.
- For `P`, we are making a `SuperPopulator` - an agent capable of populating all placeholders in one go.

#### Baseline 3 and 4

This baselines introduce information search to the `SuperPopulator`.
Making it a `ReActSuperPopulator` - a tool using ReAct agent, capable of looking up information it needs to fill the gaps.
This lookup of information is considered information search that introduces the idea of information providers.
The lookup is performed using tools: `ask_data_information_provider` and `ask_author_information_provider`, which are described in more detail below.
The tool usage loops are limited to a configured `tool_use_limit: <number>` value.

##### Baseline 3: `BL-3:-:data-provider`

Here, `C` remain unchanged.
In `P`, we equip `ReActSuperPopulator` with a `ask_data_information_provider` tool to query the data files in the given dataset.
This tool wraps a DuckDB function call, that speaks SQL to the underlying CSV files.

##### Baseline 4: `BL-4:-:author-proxy-provider`

Here, `C` remain unchanged.
In `P`, we equip `ReActSuperPopulator` with a `ask_author_information_provider` tool to query the author proxy, implemented as a RAG over the data paper for the given dataset.
This tool accepts natural language requests and returns a natural language response.

---

### Treatment

Here we introduce the whole gang of agents: `Architect` (whom we already met in Baseline 2), `Planner`, `Instructor`, `Operator`.
This gang is an assembly line that implements `M`.
The gang together is called `massi`.

The `Architect` covers the `C` part as before.
The `Planner`, `Instructor`, and `Operator` together cover `P`.


The gaps from `T` produced by the Archtiect are extracted using a pattern-matching script.
The prompt to `Planenr` lists these script-extracted gaps and the original template.
The `Planner` contextualises the gaps from the template produced by the `Architect` and describes them with additional context about the metadata template.
Per each gap, it formulates a natural language request, `r`, for information in this gap.
Specifically, it answers the question `what is this gap and what information do we need to fill it?`.
The prompt asks it to return a structured list of all and exactly all gaps contextualized.
Downstream agents receive only the gaps that correspond to those extracted by the script.

The `Instructor` is a good friend of the `Operator` and knows what tools are available to it.
It then transforms `r`, into an instruction, `i`, such that it describes a strategy for the operator to retrieve this information.
Specifically, it answers the question: `given the Operator's information provider is X, how should it search for the information needed to fill this gap?`.

The `Operator` is the final agent, similar to `ReActSuperPopulator`.
Namely, it is a ReAct agent with the same tools as `ReActSuperPopulator`, and prompt that differs from `ReActSuperPopulator` by targeting only "one gap" instead of "all gaps", and given the `r` and `i` specifications.
So, it relies on its ReAct reasoning to fulfill `r`, following `i`, and using the available tool.
Essentially, it is asked to populate a gap specified in `r` for the template `T`, as presecribed by `i`.

#### Treatment `T1:-:data-provider`

`massi` is configured to use `ask_data_information_provider`.

##### Treatment `T2:-:author-proxy-provider`

`massi` is configured to use `ask_author_information_provider`.

---

### Ablations

#### Agent Presence

Here we experiment with removing the intermediate agents.

##### Ablatiaon 1: No Planner: `AB-1`

> Question we ask: does adding gap context help?

The `Planner` agent is simply removed.
The gaps are extracted using a script.
The gaps are not contextualized.
So the request remains empty, only the gap identity is passed downstream.
The full list is sent downstream.

##### Ablatiaon 2: No Instructor: `AB-2`

> Question we ask: does adding instructions help?

The `Instructor` agent is simply removed.
The gaps are still contextualized by the `Planner`.
The instruction for the gaps remains empty.

##### Ablatiaon 3: No Planner, No Instructor: `AB-3`

> Question we ask: does applying operator per gap help (in comparison to `BL-3`, and `BL-4`?

The `Operator` works on the gaps one by one, without any additional information.

##### Ablation 4: No information providers: `AB-4`

> Question we ask: does giving context and instructions when no information search tools are available help?

The `Instructor` receives "no tools" when it reads what is available for the `Operator`.
The `Operator` receives "no tool" when it is informed about what it can use, and there are no tools bound to it technically.
The rest remains untouched.

#### Underlying LLM Models

> [!WARNING]
>
> Open question: I don't know if this is necessary.

##### Ablation 5: Small models in `massi` only: `AB-5`

---

> [!WARNING]
>
> Open question: how to choose the right small model here?

---

> Question we ask: do the result transfer acros LLM choices?

We replace all underlying LLMs in `massi` agents with a 'small' model: `K2 Horizon 7B`.

#### `tool_usage_limit` Values

> [!WARNING]
>
> Open question: I don't know if this is necessary.

##### Ablations 6-8: Different value tiers (`n := 5,10,15`): `AB-6...AB-8`

---

> [!WARNING]
>
> Open question: how to choose the right tool_usage_limit value here?

---

> Question we ask: does increasing `tool_usage_limit` help?

We replace the value of `tool_usage_limit` with `n`.
"""
