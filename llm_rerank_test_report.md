# LLM Rerank Test Report

Generated at: 2026-07-13T13:46:05

## Test Context

- LLM base URL: `https://open.bigmodel.cn/api/paas/v4/`
- LLM model: `glm-5.1`
- Database: `data/local.db`
- Ranking run id: `17`
- Ranking mode: `library`
- Embedding backend used by local ranker: `sentence-transformers`
- Embedding model/cache name: `sentence-transformers:sentence-transformers/all-MiniLM-L6-v2`
- Local ranked candidates sent to LLM: `20`
- Final top K: `5`

## System Prompt

```text
You are an academic paper recommendation reranker.
Select the papers that best match the compact user research profile.
Return strict JSON only. Do not add Markdown fences or explanatory text.
Use only candidate external_id values supplied in the request.
```

## User Prompt Payload

```json
{
  "task": "Select and explain the best 5 papers for this user.",
  "privacy_note": "This is a compressed local profile, not the user's full Zotero library.",
  "local_ranking": {
    "run_id": 17,
    "ranking_method": "library",
    "embedding_model": "sentence-transformers:sentence-transformers/all-MiniLM-L6-v2"
  },
  "user_profile": {
    "research_summary": "The user's research centers on large language models (LLMs) and the development of AI agents, with a strong emphasis on multi-agent collaboration and decentralized coordination. They are particularly interested in retrieval-augmented generation (RAG), long-context processing, and data-driven training methods to enhance LLM information utilization. Additionally, their work explores advanced LLM applications such as any-to-any multimodal generation and evolutionary coding agents for algorithmic and scientific discovery.",
    "explicit_interests": [
      "large language models",
      "retrieval augmented generation",
      "AI agents"
    ],
    "inferred_keywords": [
      "large language models",
      "retrieval augmented generation",
      "ai agents",
      "multi-agent systems",
      "long context processing",
      "evolutionary coding agents",
      "multimodal llms",
      "decentralized agent coordination",
      "llm training",
      "algorithmic discovery",
      "llms",
      "research"
    ]
  },
  "candidates": [
    {
      "external_id": "2607.08662v1",
      "title": "WebSwarm: Recursive Multi-Agent Orchestration for Deep-and-Wide Web Search",
      "authors": [
        "Xiaoshuai Song",
        "Liancheng Zhang",
        "Kangzhi Zhao",
        "Yutao Zhu",
        "Zhongyuan Wang",
        "Guanting Dong",
        "Jinghan Yang",
        "Han Li"
      ],
      "abstract": "Large language model (LLM)-based web search agents are transforming information seeking from simple factoid question answering into complex, deep-and-wide search and research-oriented tasks. A single ReAct-style agent is constrained by one long trajectory and limited context, making it difficult to handle depth and coverage simultaneously. Existing multi-agent systems improve search coverage through parallel execution and aggregation, but still exhibit clear limitations in recursive depth, collaboration adaptability, and evidence-grounded expansion. We propose WebSwarm, a progressive recursive delegation framework that jointly constructs task decomposition, recursive expansion, and agent collaboration during inference. WebSwarm dynamically instantiates agentic search nodes, each coupling a local objective with a search mode that specifies how the node should organize search and collaboration. Each node can either solve its objective itself or further delegate child nodes; after solving, it returns evidence and results upward, enabling parent nodes to further expand, revise, or aggregate the search process. To guide this process, WebSwarm first probes how task-relevant information is organized on the web to ground subsequent node expansion, and reuses process-level experience across homogeneous sibling nodes. Experiments on BrowseComp-Plus, WideSearch, DeepWideSearch, and GISA show that WebSwarm consistently outperforms single-agent and multi-agent baselines on deep, wide, and",
      "categories": [
        "cs.CL",
        "cs.AI",
        "cs.MA"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08662v1",
      "local_score": 0.5152
    },
    {
      "external_id": "2607.08768v1",
      "title": "UniClawBench: A Universal Benchmark for Proactive Agents on Real-World Tasks",
      "authors": [
        "Zhekai Chen",
        "Chengqi Duan",
        "Kaiyue Sun",
        "Bohao Li",
        "Yuqing Wang",
        "Manyuan Zhang",
        "Xihui Liu"
      ],
      "abstract": "The rapid development of large language models and multimodal large language models has accelerated the emergence of proactive agents capable of operating everyday tools and assisting users in real-world environments. However, existing benchmarks struggle to evaluate such agents effectively, as they often rely on sandboxed environments and single-turn evaluation paradigms. Moreover, their scenario-based task taxonomies mix multiple model capabilities within the same task category, making it difficult to identify the root causes of agent failures. To address these limitations, we introduce UniClawBench, the first capability-driven benchmark designed to evaluate proactive agents in dynamic, real-world settings. UniClawBench is built around five foundational model capabilities: Skill Usage, Exploration, Long-Context Reasoning, Multimodal Understanding, and Cross-Platform Coordination. Based on these capabilities, we design 400 bilingual real-world tasks. Unlike previous benchmarks that rely on static, pre-recorded answers, our benchmark evaluates agents in live Docker containers using fine-grained, step-by-step completion checkpoints. Furthermore, we design a closed-loop evaluation strategy comprising an executor agent, a hidden supervisor agent, and a user agent to simulate realistic multi-turn human feedback without leaking grading criteria. To disentangle base model capabilities from framework-level design choices, we evaluate state-of-the-art models under multiple agent fram",
      "categories": [
        "cs.CL"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08768v1",
      "local_score": 0.4558
    },
    {
      "external_id": "2607.08540v1",
      "title": "Improving Ad-hoc Search Effectiveness for Conversational Information Retrieval via Model Merging",
      "authors": [
        "Ahmed Rayane Kebir",
        "Jose G. Moreno",
        "Lynda Tamine"
      ],
      "abstract": "Conversational information retrieval is challenging since it requires the consideration of the conversation history which potentially gives rise to topic shifts and coreference resolution across previous turns. To address these challenges, previous work mainly rely on traditional fine-tuning of ad-hoc retrievers on conversational datasets or extrapolates their generalizability through multi-tasking. However, this mainstream approach is costly - since it requires model re-training - and exhibits catastrophic forgetting, where the model loses its foundational ad-hoc retrieval performance. In this paper, we fill this gap by introducing model merging as a training-free strategy enabling the design of a single retrieval model that operates across both ad-hoc and conversational settings with no additional fine-tuning. We conduct experiments using linear and non-linear parameter-wise merging strategies - namely Model Soup and Slerp - on standard ad-hoc search and conversational retrieval datasets. Our results demonstrate that model merging significantly enhances the ad-hoc search capabilities of conversational retrievers while improving generalizability across task-specific datasets, achieving up to 15% higher NDCG@3 under zero-shot conditions.",
      "categories": [
        "cs.IR",
        "cs.CL"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08540v1",
      "local_score": 0.4209
    },
    {
      "external_id": "2607.08646v1",
      "title": "UltraX: Refining Pre-Training Data at Scale with Adaptive Programmatic Editing",
      "authors": [
        "Xinlong Zhao",
        "Dongsheng Liu",
        "Hengyu Zhao",
        "Zixuan Fu",
        "Zheng Wang",
        "Jie Cai",
        "Jie Zhou",
        "Qiang Ma"
      ],
      "abstract": "As available training data approaches its physical limit, gains from Scaling Laws have begun to diminish. Consequently, improving Large Language Models (LLMs) now depends less on data expansion and more on higher-quality data utilization. However, in the context of large-scale corpora, existing refinement methodologies face significant limitations in quality, efficiency, and reliability: Rule-based approaches are constrained by fixed heuristics and struggle with instance-level variations; LLM-based approaches improve quality but fail to meet the efficiency and reliability requirements of large-scale data processing. To address these challenges, we propose UltraX, a function-calling refinement framework for large-scale pre-training data that completes the editing function space by introducing insertion in addition to deletion and modification, enabling fine-grained instance-level editing. Specifically, UltraX builds a reliable program-supervision generation pipeline. In this pipeline, dataset-adaptive prompt optimization first guides an expert LLM to produce high-quality end-to-end refined texts, and Line Alignment Mapping and Dynamic Context Replacement then convert original-refined text pairs into structured program supervision. Meanwhile, UltraX improves supervision quality and stabilizes the training distribution with low-confidence example filtering and ratio-controlled sampling by operation combination. During inference and execution, it normalizes and validates model ou",
      "categories": [
        "cs.CL",
        "cs.AI"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08646v1",
      "local_score": 0.4032
    },
    {
      "external_id": "2607.08724v1",
      "title": "Latent Memory Palace: Reasoning for Control as Autoregressive Variational Inference",
      "authors": [
        "Chuning Zhu",
        "Eva Xu",
        "Jose Barreiros",
        "Krishnan Srinivasan",
        "Paarth Shah",
        "Abhishek Gupta"
      ],
      "abstract": "Human decision-making is highly flexible -- some actions are taken immediately; others require longer deliberation. Language models have exhibited a similar capacity for adaptive \"reasoning.\" However, transferring this capability to continuous control policies has been challenging, as directly reasoning in language space may lack the granularity for spatial understanding and precise motions. In this work, we show that reasoning for control policies can emerge by organizing information in an autoregressive latent space reminiscent of a memory palace, where retrieval is iterative and adaptive. Our method, Latent Memory Palace (LMP), formulates reasoning as variational inference with an autoregressive latent distribution. We derive a latent-space reinforcement learning technique to tractably optimize its variational lower bound. The resulting policy, LMP-$π$, achieves strong empirical performance in simulation and real-world domains while exhibiting interpretable, adaptive allocation of test-time compute. We further show that the same framework yields a variable-length action tokenizer, LMP-$\\texttt{tok}$, which significantly improves the performance of downstream autoregressive policies. Together, these results present a new perspective on latent reasoning for control through the lens of variational inference.",
      "categories": [
        "cs.LG",
        "cs.RO"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08724v1",
      "local_score": 0.3986
    },
    {
      "external_id": "2607.08601v1",
      "title": "It Takes a MAESTRO To Prune Bad Experts",
      "authors": [
        "Palaash Goel",
        "Ayush Maheshwari",
        "Tanmoy Chakraborty"
      ],
      "abstract": "Sparsely-activated Mixture-of-Experts (MoE) language models achieve remarkable inference efficiency by activating only a small fraction of parameters per token, yet their full expert banks reside in memory at all times, creating a prohibitive deployment bottleneck. Existing structured pruning methods, largely designed for dense transformers, assess expert importance using locally derived heuristics that are blind to the interdependent nature of MoE routing. We introduce MAESTRO (Markov-chain Approximated Expert Sparsification via Transition-based ROuting), a structured pruning framework designed for MoE architectures that models autoregressive expert activation trajectories as Ergodic Markov chains whose stationary distributions encode cross-layer dependencies, yielding a globally aware importance heuristic. Evaluated across five diverse domains including Safety, Bias, and Ethics, MAESTRO outperforms state-of-the-art baselines by up to 10.61% in average performance retention under a strict 50% compression regime, while exhibiting substantially lower cross-task variance, indicating that global, routing-congruent pruning produces models that generalize more consistently across heterogeneous tasks.",
      "categories": [
        "cs.CL"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08601v1",
      "local_score": 0.3886
    },
    {
      "external_id": "2607.08763v1",
      "title": "OpenCoF: Learning to Reason Through Video Generation",
      "authors": [
        "Xinyan Chen",
        "Ziyu Guo",
        "Renrui Zhang",
        "Dongzhi Jiang",
        "Hongsheng Li"
      ],
      "abstract": "Reasoning has become a core capability for large models, especially when reliable decisions require understanding logical consequences. Recent video generation models offer a reasoning path distinct from previous Chain-of-Thought (CoT): reasoning can unfold through temporally connected frames, known as Chain-of-Frame (CoF) reasoning. However, existing video generators are primarily trained on general video corpora, still lacking diverse supervision and dedicated designs for CoF reasoning. To address this gap, we introduce OpenCoF, a framework comprising the OpenCoF-17K dataset, a reasoning video dataset spanning 11 task families, and Wan-CoF, a fine-tuned video model for studying whether diverse temporal supervision improves CoF behavior. Across four video reasoning benchmarks, Wan-CoF achieves considerable gains over the Wan2.2-I2V-A14B baseline. Building on this, we empirically explore more advanced designs for CoF capabilities, i.e., equipping the model with visual and textual reasoning tokens. This mechanism respectively captures low-level visual cues and high-level semantic priors for spatial and temporal reasoning. Through performance comparisons and attention analysis, we examine how these tokens contribute across model depth, denoising steps, space, and time. Our results suggest that stronger video reasoning requires both broad temporal supervision and explicit mechanisms for organizing intermediate reasoning state. We open-source the dataset, model, and code to facil",
      "categories": [
        "cs.CV",
        "cs.AI"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08763v1",
      "local_score": 0.3807
    },
    {
      "external_id": "2607.08716v1",
      "title": "Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents",
      "authors": [
        "Yifan Wu",
        "Lizhu Zhang",
        "Yuhang Zhou",
        "Mingyi Wang",
        "Bo Peng",
        "Serena Li",
        "Xiangjun Fan",
        "Zhuokai Zhao"
      ],
      "abstract": "In long-horizon tasks, decision-relevant state is often scattered across an expanding trajectory, while the action agent must surface it and act. As trajectories grow, task requirements, environment facts, prior attempts, diagnoses, and open subgoals can be buried in the context window or pushed beyond it, failing to influence decisions when needed. We call this failure mode \"behavioral state decay\". We study memory as an active intervention mechanism rather than passive retrieval. A separate memory agent runs alongside an unmodified action agent, updating a structured memory bank from the recent trajectory and deciding whether to inject a memory-grounded reminder or remain silent. The module is plug-and-play with frontier action agents and existing agent harnesses. Across Terminal-Bench 2.0 and $τ^2$-Bench, it improves pass@1 for both weaker and stronger action agents, with gains of +8.3 pp on Terminal-Bench and +6.8 pp on $τ^2$-Bench. Ablations show that selective intervention outperforms passive bank exposure, always-on injection, advisor-only guidance, and general retrieval. As an early step toward open-weight memory policies, we train Qwen3.5-27B on SETA using SFT and GRPO, improving validation reward and achieving partial transfer to Terminal-Bench.",
      "categories": [
        "cs.AI",
        "cs.CL"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08716v1",
      "local_score": 0.3786
    },
    {
      "external_id": "2607.08691v1",
      "title": "ProjAgent: Procedural Similarity Retrieval for Repository-Level Code Generation",
      "authors": [
        "QiHong Chen",
        "Aaron Imani",
        "Iftekhar Ahmed"
      ],
      "abstract": "Repository-level code generation requires implementing target functions while accounting for complex cross-file dependencies and project-specific conventions. Existing retrieval methods predominantly rely on lexical, structural, or semantic similarity, often overlooking repository functions that implement similar procedural logic despite differing in identifiers or application domains. We propose ProjAgent, a repository-level code generation system that introduces procedural similarity as an explicit retrieval signal. ProjAgent decomposes the target function into intermediate reasoning steps and employs an agentic workflow to retrieve repository functions that exhibit similar procedural behavior at each step. The retrieved procedural context is integrated with conventional semantic retrieval to construct a richer repository context for code generation. ProjAgent further incorporates a conservative static-analysis feedback loop that iteratively repairs generated code using compiler and static-analysis feedback. Evaluated on REPOCOD, ProjAgent achieves 41.14% Pass@1, outperforming existing retrieval-based baselines. These results demonstrate that procedural similarity is an effective and previously unexplored retrieval dimension for repository-level code generation.",
      "categories": [
        "cs.SE",
        "cs.AI",
        "cs.IR"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08691v1",
      "local_score": 0.3702
    },
    {
      "external_id": "2607.08690v1",
      "title": "A Practical Investigation of Training-free Relaxed Speculative Decoding",
      "authors": [
        "Guoxuan Xia",
        "Luka Ribar",
        "Paul Balanca"
      ],
      "abstract": "Speculative decoding accelerates sampling from an autoregressive LLM by using a faster auxiliary model to draft tokens which are then verified in parallel by the LLM. Standard speculative decoding is lossless: its rejection and resampling steps exactly preserve the LLM's sampling distribution. Recent work argues that relaxing this strict guarantee can yield further speed-ups, controlled capability-speed trade-offs, or even capability gains. We practically investigate training-free relaxed speculative decoding techniques, unify existing approaches within a shared framework, benchmark them on contemporary settings, and distil takeaways and empirical findings for practitioners. Important takeaways include: relaxation can require considerable capability evaluation unlike lossless speculative decoding, and many relaxed approaches rely on a drafter that is a good language model, making them unsuited for lightweight dedicated multi-token-prediction drafters.",
      "categories": [
        "cs.LG",
        "cs.AI"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08690v1",
      "local_score": 0.3686
    },
    {
      "external_id": "2607.08700v1",
      "title": "Do You Need a Frontier Model as a Citation Verifier? Benchmarking Rubric LLMs for Deep-Research Source Attribution",
      "authors": [
        "Ethan Leung",
        "Elias Lumer",
        "Corey Feld",
        "Austin Huber",
        "Vamse Kumar Subbiah",
        "Kevin Paul"
      ],
      "abstract": "Reinforcement learning increasingly relies on an LLM judge to score each rubric criterion, and that judge acts as the reward model during training. Before such a signal can be trusted, we need to know how capable the judge must be and how biased it is. We study this calibration question for citation quality in deep-research systems, where a search-grounded LLM must support each claim it writes with a cited source. Citation quality is a structured rubric task in which each attribution-citation pair is judged along two dimensions that require an LLM, source relevance and factual support. On an adversarial long-form benchmark, we score 8 off-the-shelf LLM judges from 3 model families against gold labels over 1,248 rubric decisions, all of which were human-reviewed and 378 of which were hard cases adjudicated from judge disagreements. Cheaper judges remain competitive across both dimensions, with GPT-5-mini attaining the strongest source-relevance pass-class F1 at 0.908 ($κ$=0.636), while on factual support the judges are statistically indistinguishable (overlapping confidence intervals), so no single model dominates. At comparable F1, the judges still differ substantially in pass-rate drift, false positive rate, and false negative rate. Scalar F1 obscures this directional bias, yet it is exactly what a downstream reinforcement learning loop would reinforce. Calibrating the judge is therefore a prerequisite for using citation rubrics as reward signals, and our results show that t",
      "categories": [
        "cs.CL"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08700v1",
      "local_score": 0.3581
    },
    {
      "external_id": "2607.08740v1",
      "title": "Workflow as Knowledge: Semantic Persistence for LLM-Mediated Workflows",
      "authors": [
        "Emanuele Quinto",
        "Carlo Andrea Rozzi",
        "Francesco Zanitti"
      ],
      "abstract": "Large language model (LLM) applications increasingly use explicit workflows for tool use, retrieval, branching, checkpointing, and human approval. Existing workflow systems already address many execution concerns. This paper proposes a Lisp-inspired but language-independent conceptual model: symbolic forms, object identity, and live-image thinking are used as explanatory lenses, not implementation commitments. In this model, workflow definitions, workflow instances, inference records, context snapshots, and dependency relations are represented as persistent knowledge objects in a shared knowledge substrate. Its central semantic distinction is between derive and infer: derive is deterministic computation over available state; infer is mediated LLM judgment under declared context and executor-controlled capability policy. The result is a preliminary conceptual account of semantic persistence: workflows do not merely produce knowledge and leave traces, but can themselves be represented as inspectable, resumable, and reviewable knowledge objects, while formal transition semantics remain future work.",
      "categories": [
        "cs.AI",
        "cs.PL",
        "cs.SE"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08740v1",
      "local_score": 0.3507
    },
    {
      "external_id": "2607.08734v1",
      "title": "The Illusion of Equivalency: Statistical Characterization of Quantization Effects in LLMs",
      "authors": [
        "Baha Rababah",
        "Cuneyt Gurcan Akcora",
        "Carson K. Leung"
      ],
      "abstract": "Post-training quantization is widely used to deploy large language models in resource-constrained settings, yet its evaluation relies almost exclusively on accuracy and perplexity. We show that these metrics fail to capture behavioral changes induced by quantization. We introduce correctness agreement, a decision-level metric that measures overlap in correct predictions between a base model and its quantized variants, independent of absolute accuracy. Across multiple models and quantization schemes from 8-bit to 2-bit, we find that behavioral divergence emerges under moderate quantization even when task performance appears preserved. To explain this effect, we analyze quantization as a structural operator on attention weights and quantify layer-wise distortions using statistical and distributional measures. Our results reveal non-linear breakpoints at low bit-widths and show that query and key projections are consistently more sensitive than value and output projections. These findings expose an illusion of equivalence between base and quantized models and motivate behavioral evaluation beyond conventional performance metrics.",
      "categories": [
        "cs.AI"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08734v1",
      "local_score": 0.3471
    },
    {
      "external_id": "2607.08758v1",
      "title": "Ideas Have Genomes: Benchmarking Scientific Lineage Reasoning and Lineage-Grounded Idea Generation",
      "authors": [
        "Yifan Zhou",
        "Qihao Yang",
        "Yan Li",
        "Donggang Li",
        "Xiru Hu",
        "Hokin Deng",
        "Ziyang Gong",
        "Xuanyi Zhou"
      ],
      "abstract": "Scientific ideas rarely start from a blank page. They inherit mechanisms, repair known limitations, and recombine pieces of earlier work, much like biological genomes. Current benchmarks still say little about whether AI systems can follow this inheritance structure. We present IdeaGene-Bench (IG-Bench), a benchmark for scientific lineage reasoning and lineage-grounded idea generation. IG-Bench is organized around the IdeaGene framework: each paper or proposal is represented as a set of minimal, typed, evidence-grounded Idea Genome objects, and a GenomeDiff aligns these objects to record inheritance, mutation, loss, external import, and novel insertion under six operational evolutionary dynamics. The benchmark contains 1,961 golden lineage traces, 1,085 curated Idea Genome objects, and 920 pairwise GenomeDiff records across 10 scientific domains. It supports two evaluations. IG-Exam (42 task types, 1,029 instances) tests closed-form lineage reasoning across Idea Genome abstraction, inheritance tracing, evolutionary reasoning, and lineage verification. IG-Arena evaluates generation with a lineage-conditioned Population-Evolution Score(PES), asking whether a proposal can be inserted as a coherent descendant of a given lineage population: it should inherit the right Idea Genome objects, vary meaningfully from nearby work, and offer selection value for future research. Experiments on 14 LLM-based scientists expose a compositional bottleneck. The strongest system reaches only 27.3",
      "categories": [
        "cs.AI"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08758v1",
      "local_score": 0.3466
    },
    {
      "external_id": "2607.08647v1",
      "title": "Multi-Modal, Multi-Environment Machine Teaching for Robust Reward Learning",
      "authors": [
        "Ali Larian",
        "Qian Lin",
        "Chang Zong Wu",
        "Daniel S. Brown"
      ],
      "abstract": "As autonomous agents are increasingly deployed across diverse operational contexts, aligning their behavior with human intent demands reward functions that remain robust to such changes rather than overfitting to any single environment. Inverse reinforcement learning (IRL) provides a principled way to infer such objectives from human feedback. However, existing analyses of optimal teaching approaches for IRL focus on single-environment, demonstration-only settings, leaving underexplored how heterogeneous feedback modalities and environment dynamics jointly constrain reward functions that generalize across multiple environments. Because demonstrations in one MDP entangle reward information with that environments specific structure, the resulting rewards frequently fail to generalize when the agent is deployed in a new setting. We first analyze how different feedback modalities constrain rewards, showing that, in the unlimited-data regime, comparisons impose strictly stronger global constraints than other modalities. Beyond this theoretical analysis, we introduce a hierarchical machine teaching algorithm for reward learning that operates across multiple MDPs. The algorithm first greedily selects informative environments that expose complementary reward constraints, then strategically queries low-cost feedback within those environments. Empirically, our method achieves substantially lower regret and stronger generalization to held-out environments than uniform teaching baselines",
      "categories": [
        "cs.LG",
        "cs.AI"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08647v1",
      "local_score": 0.3419
    },
    {
      "external_id": "2607.08602v1",
      "title": "Towards Precision Therapy in Hepatocellular Carcinoma: A Clinical-Reasoning LLM for Risk Stratification and Treatment Guidance",
      "authors": [
        "Peng Cui",
        "Jitao Wang",
        "Siyan Xue",
        "Yao Huang",
        "Haoming Xia",
        "Dong Li",
        "Dengxiang Liu",
        "Weilin Wang"
      ],
      "abstract": "Hepatocellular carcinoma (HCC) is a common malignancy and a leading cause of cancer-related mortality. Current guidelines and staging systems provide coarse categories, but often miss within-stage heterogeneity and the clinical context in electronic medical records (EMRs). We present HCC-STAR (Hepatocellular Carcinoma Staging, Treatment And pRognosis), a clinically aligned large language model that reads routine EMR narratives and jointly outputs risk score-based staging, ranked guideline-consistent treatments with evidence-based rationales, and individualized survival estimates. We curated about 30,000 HCC cases from SEER and expanded them into EMR-style narrative training data using a clinician-validated, prompt-based augmentation workflow. On this corpus, we developed a knowledge-aligned reasoning framework optimized with a step-verifiable composite reward, moving beyond text-level memorization of clinical guidelines. In a multi-center cohort of 6,668 patients from 12 hospitals in China, HCC-STAR achieved state-of-the-art performance in treatment recommendation and risk stratification compared with clinical guidelines and competitive models, including GPT-5 and Gemini-2.5 Pro. Hypothetical overall-survival analysis showed a median survival of 51 months under adherence to HCC-STAR recommendations, compared with 29 and 32 months under BCLC and CNLC. In clinician-centric evaluations, blinded hepatobiliary specialists rated HCC-STAR's reasoning and evidence-based justification",
      "categories": [
        "cs.AI"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08602v1",
      "local_score": 0.3322
    },
    {
      "external_id": "2607.08642v1",
      "title": "DominoTree: Conditional Tree-Structured Drafting with Domino for Speculative Decoding",
      "authors": [
        "Saw S. Lin",
        "Jyh-Shing Roger Jang"
      ],
      "abstract": "Speculative decoding accelerates LLM inference by drafting several tokens and verifying them in parallel. Block-diffusion drafters such as DFlash produce a draft block in one pass but model only per-position marginals; best-first tree methods such as DDTree expand candidate trees from those marginals. The released Domino drafter adds a GRU-based causal correction that makes each draft token's distribution path-dependent, a structure DDTree's factorized formulation cannot represent. We introduce DominoTree, a training-free best-first draft tree scored by Domino's conditional, non-factorized correction along each root-to-node path, made practical by restricting the per-node correction to a candidate top-M. On Qwen3-4B across eight benchmarks, DominoTree reaches up to 6.6x speedup over autoregressive decoding and the highest mean accept length of any evaluated method, up to 10.7 tokens per round, at every temperature we test. DominoTree constructs its tree with a GPU-native, CUDA-graph builder that is bit-identical to a reference Python implementation, so acceptance is unchanged, while keeping per-round tree construction cheap. With this builder as default, DominoTree wins throughput over the released Domino decoder at every temperature, 9-10% overall on Qwen3-4B and up to +22% on Alpaca, and over DDTree/CaDDTree at every temperature we test. On Qwen3- 8B, DominoTree keeps the highest accepted length at every temperature and adds a decisive throughput win at T=0, +24% over DDTre",
      "categories": [
        "cs.CL"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08642v1",
      "local_score": 0.3242
    },
    {
      "external_id": "2607.08625v1",
      "title": "The complexities of patient-centred conversational artificial intelligence",
      "authors": [
        "João Matos",
        "Olivia Buege",
        "Donny Cheung",
        "Gary S. Collins",
        "Paula Dhiman",
        "Nan Li",
        "Bingyu Mao",
        "Benjamin W. Nelson"
      ],
      "abstract": "Consumer-facing health chatbots powered by large language models (LLMs) are increasingly used for symptom assessment. However, chatbot development and evaluation often rely on cooperative, articulate, simulated patients. We analysed 2,053 real patient-chatbot conversations and found that communication patterns and expression of emotions vary widely across users. We developed a patient simulator that separately models clinical content, emotional state, conversational strategy, and communication style. In a Turing-inspired evaluation of realism with 15 human graders, simulated conversations were nearly indistinguishable from real ones, with human graders achieving an accuracy of 55%. We used five distinct patient personae, across 1,164 clinician-graded cases, to evaluate the performance of four LLMs in urgency assessment. We found that communication style can significantly alter triage outcomes. Patient-centred conversational artificial intelligence must accommodate communication diversity: systems designed for idealised, rather than realistic, interactions risk underperforming and amplifying health disparities when deployed in the real world.",
      "categories": [
        "cs.AI",
        "cs.CL"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08625v1",
      "local_score": 0.3212
    },
    {
      "external_id": "2607.08641v1",
      "title": "Steering Neural Network Training through Interpretable Constraints Based on Partial Dependence",
      "authors": [
        "Yann Claes",
        "Pierre Geurts",
        "Vân Anh Huynh-Thu"
      ],
      "abstract": "Over the last few years, there has been an increased interest in making machine learning models more interpretable. Although a great deal of effort goes into developing techniques for interpreting the interactions learned by a given model, fewer studies focus on assessing the quality of such explanations. Even fewer focus on how to adjust the model to produce explanations faithful to prior knowledge, a process known as explanation-guided learning. Furthermore, most approaches in this area focus on classification problems and usually assume prior knowledge about which input features or regions are most important. In this work, we introduce a new approach to steering neural networks based on partial dependence, such that their average response to certain features aligns with specific functional domain knowledge about the problem. We empirically demonstrate on a range of regression problems, including dynamical systems forecasting, that models whose training has been controlled using our method perform better than unconstrained models and are more data-efficient. Moreover, we highlight that interpretations obtained from the former actually align with the user-provided knowledge, whereas those obtained from the latter do not.",
      "categories": [
        "cs.LG"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08641v1",
      "local_score": 0.3199
    },
    {
      "external_id": "2607.08665v1",
      "title": "Resample or Reroute? Budget-Aware Test-Time Model Selection for Large Language Models",
      "authors": [
        "Teng-Ruei Chen"
      ],
      "abstract": "Routing among large language models (LLMs) trades response quality against serving cost, motivated by the reported gap between deployed routers and a per-instance oracle. Recent analysis shows that test-time resampling can recover per-instance selection headroom that no single-commit router captures; however, that guarantee holds only under an idealized oracle equipped with correctness labels and an unconstrained budget, neither of which a deployed system has. To the best of our knowledge, no previous work treats resampling the committed model and rerouting to an alternative model as competing uses of a single per-query cost budget. Therefore, this work formulates budget-aware test-time model selection: given a per-query budget and an imperfect verifier, allocate each unit of budget between resampling and rerouting so that expected correctness is maximized. An online resample-or-reroute (RoR) allocation policy driven by estimated marginal correctness per unit cost is proposed, and its behavior is grounded in the recoverability asymmetry between selection and sampling. Replay experiments on newly regenerated multi-draw correctness tensors from an eleven-model open-weight pool over four benchmarks of differing difficulty show that the proposed RoR policy attains a favorable cost-quality Pareto front relative to single-route, one-commit-router, budget-aware best-of-K, cascade, and random-allocation baselines for the tested pools, with the largest gains on the most heterogeneous ",
      "categories": [
        "cs.LG"
      ],
      "published_date": "2026-07-09",
      "url": "http://arxiv.org/abs/2607.08665v1",
      "local_score": 0.3184
    }
  ],
  "output_schema": {
    "selected_papers": [
      {
        "external_id": "must exactly match a candidate external_id",
        "rerank_score": "number from 0 to 1",
        "one_sentence_summary": "one concise sentence",
        "why_recommended": "specific explanation tied to user interests",
        "related_user_interests": [
          "research interest phrase"
        ],
        "reading_priority": "high, medium, or low"
      }
    ]
  },
  "constraints": [
    "Return at most 5 selected_papers.",
    "Do not recommend papers not present in candidates.",
    "Ground reasons in candidate metadata and the compressed user profile."
  ]
}
```

## Raw LLM Response

```json
{
  "selected_papers": [
    {
      "external_id": "2607.08662v1",
      "rerank_score": 0.95,
      "one_sentence_summary": "WebSwarm introduces a progressive recursive delegation framework for LLM-based multi-agent web search that dynamically instantiates agentic nodes for collaborative, deep-and-wide information seeking.",
      "why_recommended": "This paper directly aligns with the user's core interests in multi-agent collaboration and decentralized coordination, demonstrating how LLM-based agents can recursively decompose tasks and coordinate to handle complex research-oriented searches.",
      "related_user_interests": [
        "multi-agent systems",
        "decentralized agent coordination",
        "ai agents",
        "large language models"
      ],
      "reading_priority": "high"
    },
    {
      "external_id": "2607.08768v1",
      "rerank_score": 0.90,
      "one_sentence_summary": "UniClawBench is a capability-driven benchmark for evaluating proactive agents in real-world settings across five foundational dimensions including long-context reasoning and multimodal understanding.",
      "why_recommended": "The paper evaluates proactive AI agents specifically on long-context reasoning and multimodal understanding, which are explicitly highlighted in the user's research profile as key areas of interest for LLM applications.",
      "related_user_interests": [
        "ai agents",
        "long context processing",
        "multimodal llms"
      ],
      "reading_priority": "high"
    },
    {
      "external_id": "2607.08716v1",
      "rerank_score": 0.88,
      "one_sentence_summary": "This paper proposes a proactive memory agent that runs alongside an action agent to mitigate behavioral state decay by selectively injecting reminders from a structured memory bank in long-horizon tasks.",
      "why_recommended": "It tackles the critical challenge of long-context processing for AI agents, proposing an active memory intervention mechanism that perfectly matches the user's focus on enhancing LLM information utilization over long trajectories.",
      "related_user_interests": [
        "ai agents",
        "long context processing",
        "large language models"
      ],
      "reading_priority": "high"
    },
    {
      "external_id": "2607.08758v1",
      "rerank_score": 0.85,
      "one_sentence_summary": "IdeaGene-Bench introduces a benchmark for scientific lineage reasoning and lineage-grounded idea generation, modeling idea inheritance and evolution through structured GenomeDiff records.",
      "why_recommended": "This work resonates strongly with the user's interest in evolutionary coding agents and algorithmic/scientific discovery, providing a framework to evaluate how AI systems reason about and generate scientific ideas through evolutionary dynamics.",
      "related_user_interests": [
        "evolutionary coding agents",
        "algorithmic discovery",
        "ai agents"
      ],
      "reading_priority": "high"
    },
    {
      "external_id": "2607.08691v1",
      "rerank_score": 0.82,
      "one_sentence_summary": "ProjAgent is a repository-level code generation system that uses an agentic workflow to retrieve procedurally similar code, integrating this context to enhance LLM generation.",
      "why_recommended": "The paper bridges the user's interests in retrieval-augmented generation (RAG) and coding agents, introducing procedural similarity retrieval as a new RAG signal for improving LLM performance in complex code generation tasks.",
      "related_user_interests": [
        "retrieval augmented generation",
        "ai agents",
        "large language models"
      ],
      "reading_priority": "medium"
    }
  ]
}
```

## Parsed Final Recommendations

```json
[
  {
    "rank": 1,
    "external_id": "2607.08662v1",
    "title": "WebSwarm: Recursive Multi-Agent Orchestration for Deep-and-Wide Web Search",
    "authors": [
      "Xiaoshuai Song",
      "Liancheng Zhang",
      "Kangzhi Zhao",
      "Yutao Zhu",
      "Zhongyuan Wang",
      "Guanting Dong",
      "Jinghan Yang",
      "Han Li",
      "Kun Gai",
      "Ji-Rong Wen",
      "Zhicheng Dou"
    ],
    "local_score": 0.515213,
    "llm_score": 0.95,
    "reading_priority": "high",
    "one_sentence_summary": "WebSwarm introduces a progressive recursive delegation framework for LLM-based multi-agent web search that dynamically instantiates agentic nodes for collaborative, deep-and-wide information seeking.",
    "why_recommended": "This paper directly aligns with the user's core interests in multi-agent collaboration and decentralized coordination, demonstrating how LLM-based agents can recursively decompose tasks and coordinate to handle complex research-oriented searches.",
    "related_user_interests": [
      "multi-agent systems",
      "decentralized agent coordination",
      "ai agents",
      "large language models"
    ],
    "url": "http://arxiv.org/abs/2607.08662v1"
  },
  {
    "rank": 2,
    "external_id": "2607.08768v1",
    "title": "UniClawBench: A Universal Benchmark for Proactive Agents on Real-World Tasks",
    "authors": [
      "Zhekai Chen",
      "Chengqi Duan",
      "Kaiyue Sun",
      "Bohao Li",
      "Yuqing Wang",
      "Manyuan Zhang",
      "Xihui Liu"
    ],
    "local_score": 0.455828,
    "llm_score": 0.9,
    "reading_priority": "high",
    "one_sentence_summary": "UniClawBench is a capability-driven benchmark for evaluating proactive agents in real-world settings across five foundational dimensions including long-context reasoning and multimodal understanding.",
    "why_recommended": "The paper evaluates proactive AI agents specifically on long-context reasoning and multimodal understanding, which are explicitly highlighted in the user's research profile as key areas of interest for LLM applications.",
    "related_user_interests": [
      "ai agents",
      "long context processing",
      "multimodal llms"
    ],
    "url": "http://arxiv.org/abs/2607.08768v1"
  },
  {
    "rank": 3,
    "external_id": "2607.08716v1",
    "title": "Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents",
    "authors": [
      "Yifan Wu",
      "Lizhu Zhang",
      "Yuhang Zhou",
      "Mingyi Wang",
      "Bo Peng",
      "Serena Li",
      "Xiangjun Fan",
      "Zhuokai Zhao"
    ],
    "local_score": 0.378599,
    "llm_score": 0.88,
    "reading_priority": "high",
    "one_sentence_summary": "This paper proposes a proactive memory agent that runs alongside an action agent to mitigate behavioral state decay by selectively injecting reminders from a structured memory bank in long-horizon tasks.",
    "why_recommended": "It tackles the critical challenge of long-context processing for AI agents, proposing an active memory intervention mechanism that perfectly matches the user's focus on enhancing LLM information utilization over long trajectories.",
    "related_user_interests": [
      "ai agents",
      "long context processing",
      "large language models"
    ],
    "url": "http://arxiv.org/abs/2607.08716v1"
  },
  {
    "rank": 4,
    "external_id": "2607.08758v1",
    "title": "Ideas Have Genomes: Benchmarking Scientific Lineage Reasoning and Lineage-Grounded Idea Generation",
    "authors": [
      "Yifan Zhou",
      "Qihao Yang",
      "Yan Li",
      "Donggang Li",
      "Xiru Hu",
      "Hokin Deng",
      "Ziyang Gong",
      "Xuanyi Zhou",
      "Huacan Wang",
      "Xiangchao Yan",
      "Wanghan Xu",
      "Wenlong Zhang",
      "Shaofeng Zhang",
      "Yue Zhou",
      "Yifan Yang",
      "Zhihang Zhong",
      "Xue Yang"
    ],
    "local_score": 0.34659,
    "llm_score": 0.85,
    "reading_priority": "high",
    "one_sentence_summary": "IdeaGene-Bench introduces a benchmark for scientific lineage reasoning and lineage-grounded idea generation, modeling idea inheritance and evolution through structured GenomeDiff records.",
    "why_recommended": "This work resonates strongly with the user's interest in evolutionary coding agents and algorithmic/scientific discovery, providing a framework to evaluate how AI systems reason about and generate scientific ideas through evolutionary dynamics.",
    "related_user_interests": [
      "evolutionary coding agents",
      "algorithmic discovery",
      "ai agents"
    ],
    "url": "http://arxiv.org/abs/2607.08758v1"
  },
  {
    "rank": 5,
    "external_id": "2607.08691v1",
    "title": "ProjAgent: Procedural Similarity Retrieval for Repository-Level Code Generation",
    "authors": [
      "QiHong Chen",
      "Aaron Imani",
      "Iftekhar Ahmed"
    ],
    "local_score": 0.370175,
    "llm_score": 0.82,
    "reading_priority": "medium",
    "one_sentence_summary": "ProjAgent is a repository-level code generation system that uses an agentic workflow to retrieve procedurally similar code, integrating this context to enhance LLM generation.",
    "why_recommended": "The paper bridges the user's interests in retrieval-augmented generation (RAG) and coding agents, introducing procedural similarity retrieval as a new RAG signal for improving LLM performance in complex code generation tasks.",
    "related_user_interests": [
      "retrieval augmented generation",
      "ai agents",
      "large language models"
    ],
    "url": "http://arxiv.org/abs/2607.08691v1"
  }
]
```
