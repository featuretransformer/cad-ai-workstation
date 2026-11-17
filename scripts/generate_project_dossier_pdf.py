"""
Generates the comprehensive PDF dossier for the CAD AI Workstation project.
Compiles executive synopsis, architecture, file breakdown, complete technologies & resources,
project progression history, bug fixes, LangGraph deep-dive, mechanical engineering considerations,
and tricky interview questions into a high-fidelity document printed via Chrome headless.
"""
import os
import subprocess
import sys

def build_html_content() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CAD AI Workstation — Project Synopsis, Architecture & Technical Defense Guide</title>
<style>
  @page {
    size: A4;
    margin: 14mm 14mm 14mm 14mm;
    @bottom-right {
      content: counter(page);
    }
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    line-height: 1.55;
    font-size: 10.5pt;
    background: #ffffff;
    margin: 0;
    padding: 0;
  }

  h1, h2, h3, h4 {
    color: #0f172a;
    font-weight: 700;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
  }

  h1 {
    font-size: 22pt;
    line-height: 1.2;
    border-bottom: 3px solid #0284c7;
    padding-bottom: 8px;
    margin-top: 0;
  }

  h2 {
    font-size: 14pt;
    border-bottom: 1.5px solid #cbd5e1;
    padding-bottom: 4px;
    margin-top: 1.6em;
    color: #0369a1;
  }

  h3 {
    font-size: 11.5pt;
    color: #0f172a;
    margin-top: 1.1em;
  }

  h4 {
    font-size: 10.5pt;
    color: #334155;
    margin-bottom: 0.2em;
  }

  p {
    margin-top: 0.3em;
    margin-bottom: 0.6em;
  }

  .header-box {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #ffffff;
    padding: 24px;
    border-radius: 8px;
    margin-bottom: 24px;
  }

  .header-box h1 {
    color: #38bdf8;
    border-bottom: 2px solid rgba(56, 189, 248, 0.4);
    margin-top: 0;
    font-size: 24pt;
  }

  .header-subtitle {
    font-size: 12pt;
    color: #94a3b8;
    margin-top: 4px;
    margin-bottom: 12px;
  }

  .badge-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }

  .badge {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 8.5pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .callout {
    border-left: 4px solid #0284c7;
    background: #f0f9ff;
    padding: 10px 14px;
    margin: 12px 0;
    border-radius: 0 6px 6px 0;
    page-break-inside: avoid;
  }

  .callout-title {
    font-weight: 700;
    color: #0369a1;
    font-size: 9.5pt;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .callout-warning {
    border-left-color: #f59e0b;
    background: #fffbeb;
  }
  .callout-warning .callout-title {
    color: #b45309;
  }

  .callout-success {
    border-left-color: #10b981;
    background: #ecfdf5;
  }
  .callout-success .callout-title {
    color: #047857;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 18px 0;
    font-size: 9pt;
    page-break-inside: avoid;
  }

  th, td {
    padding: 7px 10px;
    border: 1px solid #cbd5e1;
    text-align: left;
    vertical-align: top;
  }

  th {
    background-color: #f1f5f9;
    font-weight: 700;
    color: #1e293b;
    border-bottom: 2px solid #94a3b8;
  }

  tr:nth-child(even) {
    background-color: #f8fafc;
  }

  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 8.5pt;
    background: #f1f5f9;
    padding: 2px 4px;
    border-radius: 3px;
    color: #0f172a;
    border: 1px solid #e2e8f0;
  }

  pre {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    background: #0f172a;
    color: #f8fafc;
    padding: 10px 12px;
    border-radius: 6px;
    font-size: 8pt;
    line-height: 1.4;
    overflow-x: auto;
    page-break-inside: avoid;
  }

  .qa-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-top: 3px solid #0284c7;
    border-radius: 6px;
    padding: 12px 14px;
    margin-bottom: 14px;
    page-break-inside: avoid;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }

  .qa-question {
    font-weight: 700;
    color: #0f172a;
    font-size: 10.5pt;
    margin-bottom: 6px;
  }

  .qa-answer {
    color: #334155;
    font-size: 9.5pt;
    line-height: 1.5;
  }

  .page-break {
    page-break-before: always;
  }

  .meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
    font-size: 9pt;
  }

  .meta-item {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 8px 12px;
    border-radius: 4px;
  }
  .meta-label {
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    font-size: 7.5pt;
  }
  .meta-value {
    color: #0f172a;
    font-weight: 600;
    margin-top: 2px;
  }
</style>
</head>
<body>

<!-- COVER / HEADER BLOCK -->
<div class="header-box">
  <h1>CAD AI Workstation</h1>
  <div class="header-subtitle">Comprehensive System Architecture, Technical Synopsis & Mechanical Engineering Defense Guide</div>
  <p style="color: #cbd5e1; font-size: 10pt; max-width: 90%;">
    An autonomous multi-agent engineering platform that translates multimodal natural language prompts and mechanical engineering drawings into manufacturing-ready, parametric 3D CAD models (STEP, STL, GLB) and downstream production documentation using LangGraph, CADIR, and OpenCASCADE.
  </p>
  <div class="badge-container">
    <span class="badge">LangGraph Multi-Agent</span>
    <span class="badge">OpenCASCADE / build123d</span>
    <span class="badge">CADIR Parametric Tree</span>
    <span class="badge">FastAPI + Celery + Redis</span>
    <span class="badge">Next.js 14 + Three.js</span>
    <span class="badge">B-Rep & DFM Compliant</span>
  </div>
</div>

<!-- SECTION 1 -->
<h2>1. Executive Project Synopsis</h2>

<h3>The 2-Minute Elevator Pitch</h3>
<div class="callout callout-success">
  <div class="callout-title">Core Value Proposition</div>
  <p>
    <strong>CAD AI Workstation</strong> is an industrial-grade, multi-agent AI system that converts natural language requirements and engineering sketches into production-ready 3D CAD models (STEP B-Rep, STL mesh, GLB) and downstream manufacturing packages (DFM analysis, CNC toolpath setups, Bill of Materials).
  </p>
  <p>
    Unlike conventional generative AI tools that produce "dumb", un-editable triangular polygonal meshes (NeRFs/diffusion) or hallucinate non-functional Python code, our platform leverages a <strong>compiled LangGraph state machine</strong> combined with a proprietary <strong>CAD Intermediate Representation (CADIR)</strong>. The system isolates generative AI to parametric CSG schema synthesis, deterministically compiles the representation through an OpenCASCADE kernel (via <code>build123d</code>), and validates topology with automated closed-loop self-healing.
  </p>
</div>

<h3>The 5-Minute Technical Overview</h3>
<p>
  Mechanical CAD requires mathematical exactness, continuity of boundaries ($C^0, C^1, G^2$), and strict feature dependency trees. Applying Large Language Models directly to CAD code fails because:
</p>
<ul>
  <li><strong>API Hallucination & Code Fragility:</strong> OpenCASCADE and CadQuery have massive, stateful APIs. A single hallucinated method or syntax error causes total failure.</li>
  <li><strong>Lack of Spatial Precision:</strong> Statistical language models cannot accurately calculate 3D geometric intersections, complex face normal vectors, or non-trivial trigonometric tangencies.</li>
  <li><strong>Meshes vs. Solids:</strong> Generative 3D vision models produce triangular surface meshes (STLs/OBJs). Manufacturing systems (CNC machines, CMM inspection, injection molds) require exact <strong>B-Rep (Boundary Representation)</strong> solids with analytic cylinders, planes, and NURBS curves stored in STEP format.</li>
</ul>
<p>
  Our platform solves these fundamental barriers through a 4-pillar architectural foundation:
</p>
<ol>
  <li><strong>CADIR (CAD Intermediate Representation):</strong> A strict Pydantic v2 JSON specification representing 2D sketch primitives, 3D CSG features (extrude, revolve, holes, counterbores, fillets, spur gears, springs), and explicit dependency graphs.</li>
  <li><strong>Deterministic Code Interpretation:</strong> An independent interpreter converts valid CADIR into deterministic, production-grade <code>build123d</code> / OpenCASCADE code.</li>
  <li><strong>Sandboxed Physical Validation:</strong> Runs in an isolated sub-process checking volume, surface area, B-Rep manifoldness, and Euler-Poincaré invariants ($V - E + F - (H - 2P) = 2$).</li>
  <li><strong>Self-Healing Feedback Loop:</strong> If the CADIR fails validation or OpenCASCADE flags topological errors, the exact stack trace and geometric fault are fed back to an autonomous repair agent for targeted remediation (up to 3 automated attempts).</li>
</ol>

<div class="page-break"></div>

<!-- SECTION 2 -->
<h2>2. Technologies and Resources Used in the Project</h2>
<p>
  The project is engineered as a robust, microservices-ready full-stack architecture combining high-performance geometry kernels, asynchronous distributed workers, stateful agent graphs, and modern interactive WebGL interfaces.
</p>

<table>
  <thead>
    <tr>
      <th style="width: 20%;">Category</th>
      <th style="width: 25%;">Technology / Library</th>
      <th style="width: 15%;">Version</th>
      <th style="width: 40%;">Role & Architectural Significance</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="2"><strong>CAD Kernel & Geometry</strong></td>
      <td><code>build123d</code> / OCP</td>
      <td><code>0.13.0</code></td>
      <td>High-level declarative parametric CAD library built directly on OpenCASCADE Technology (OCCT). Replaces procedural C++ calls with safe, deterministic 1D/2D/3D contexts.</td>
    </tr>
    <tr>
      <td><code>OpenCASCADE (OCCT)</code></td>
      <td><code>7.x+</code></td>
      <td>Industry-standard industrial C++ CAD modeling kernel. Generates true B-Rep NURBS geometry and exports STEP AP203/AP214/AP242 files.</td>
    </tr>
    <tr>
      <td rowspan="3"><strong>3D Mesh & File Conversion</strong></td>
      <td><code>trimesh</code></td>
      <td><code>4.5.2</code></td>
      <td>Calculates exact watertightness, bounding box envelopes, surface areas, center of mass, and inertia tensors.</td>
    </tr>
    <tr>
      <td><code>pygltflib</code> / <code>cadquery</code></td>
      <td><code>1.16.2</code></td>
      <td>Tessellates B-Rep solids into compressed binary glTF (<code>.glb</code>) models for real-time browser rendering.</td>
    </tr>
    <tr>
      <td><code>scipy</code> / <code>numpy</code></td>
      <td>Latest</td>
      <td>Executes <code>cKDTree</code> spatial indexing for Chamfer Distance, Directed Hausdorff Distance, and 3D voxel grid calculations.</td>
    </tr>
    <tr>
      <td rowspan="3"><strong>AI & Agent Orchestration</strong></td>
      <td><code>langgraph</code></td>
      <td><code>>=0.2.45</code></td>
      <td>Cyclic state-machine agent orchestrator. Manages complex multi-branch routing, sequential decomposition, and the self-healing retry loop.</td>
    </tr>
    <tr>
      <td><code>langchain-core</code></td>
      <td><code>>=0.3.15</code></td>
      <td>Foundation schemas, prompt templates, and structured LLM tool integration.</td>
    </tr>
    <tr>
      <td><code>langchain-groq</code><br><code>langchain-google-genai</code></td>
      <td><code>>=0.2.1</code><br><code>>=2.0.4</code></td>
      <td><strong>Groq:</strong> LLaMA-3.3-70B-Versatile for ultra-fast (1-2s) text generation.<br><strong>Gemini:</strong> Gemini-Flash for multimodal reasoning (engineering drawings and sketches).</td>
    </tr>
    <tr>
      <td rowspan="3"><strong>Backend API & Workers</strong></td>
      <td><code>fastapi</code> + <code>uvicorn</code></td>
      <td><code>0.115.0</code></td>
      <td>Asynchronous high-performance REST API. Handles requests, SSE telemetry streaming, and file downloads.</td>
    </tr>
    <tr>
      <td><code>celery</code> + <code>redis</code></td>
      <td><code>5.4.0</code> / <code>5.2.0</code></td>
      <td>Distributed background worker system. Decouples long-running CAD geometry kernel execution from web request threads.</td>
    </tr>
    <tr>
      <td><code>pydantic</code> (v2)</td>
      <td><code>2.9.2</code></td>
      <td>Strict schema definition and validation for CADIR bytecode, enforcing positive numeric bounds and required parameters.</td>
    </tr>
    <tr>
      <td rowspan="2"><strong>Database & Storage</strong></td>
      <td><code>PostgreSQL</code> + <code>SQLAlchemy</code></td>
      <td><code>2.0.35</code></td>
      <td>Relational persistence for sessions, designs, base64 image data, CADIR trees, and manufacturing reports.</td>
    </tr>
    <tr>
      <td><code>Alembic</code></td>
      <td><code>1.13.3</code></td>
      <td>Automated, idempotent database schema migrations ensuring zero-downtime column upgrades.</td>
    </tr>
    <tr>
      <td rowspan="4"><strong>Frontend Web Application</strong></td>
      <td><code>Next.js</code> (App Router)</td>
      <td><code>14.2.5</code></td>
      <td>React-based enterprise web framework providing server-side rendering, routing, and asset optimization.</td>
    </tr>
    <tr>
      <td><code>React</code> + <code>TypeScript</code></td>
      <td><code>18.3.1</code> / <code>5.6.2</code></td>
      <td>Type-safe user interface development ensuring end-to-end data integrity.</td>
    </tr>
    <tr>
      <td><code>Three.js</code> / <code>@react-three/fiber</code></td>
      <td><code>0.168.0</code> / <code>8.17.0</code></td>
      <td>WebGL 3D engine rendering interactive CAD models with orbit controls, procedural studio lighting, and grid axes.</td>
    </tr>
    <tr>
      <td><code>TailwindCSS</code> + <code>Lucide</code></td>
      <td><code>3.4.13</code></td>
      <td>Utility-first responsive styling and professional CAD workstation iconography.</td>
    </tr>
    <tr>
      <td><strong>Engineering Datasets</strong></td>
      <td>DeepCAD, Fusion360 Gallery, BenchCAD</td>
      <td>Read-Only</td>
      <td>Tens of thousands of real-world mechanical CAD construction sequences used as few-shot exemplars and benchmarking ground truth.</td>
    </tr>
  </tbody>
</table>

<div class="page-break"></div>

<!-- SECTION 3 -->
<h2>3. Comprehensive File-by-File Breakdown ("In Simple Words")</h2>

<p>Every file in the codebase has a distinct, single-responsibility role. Below is an exhaustive structural breakdown:</p>

<h3>Core Orchestration & Infrastructure</h3>
<ul>
  <li><code>run.py</code>: The master launcher. Detects ports, resolves process collisions, verifies Windows C-extension DLL stability (e.g., <code>_ssl</code>), and starts backend, worker, and frontend.</li>
  <li><code>docker-compose.yml</code>: Configures containerized multi-service deployment for Postgres, Redis, MinIO S3, Backend API, Worker, and Frontend.</li>
  <li><code>architecture_specification.md</code>: The definitive 100-page system specification detailing CADIR standards, mathematical metric formulas, and pipeline invariants.</li>
</ul>

<h3>Backend Core (`backend/`)</h3>
<ul>
  <li><code>main.py</code>: The entry point for FastAPI. Mounts CORS, static export directories, API route routers, and initializes database auto-migrations on startup.</li>
  <li><code>config.py</code>: Central configuration hub reading environment variables for databases, Redis, Groq/Gemini API keys, and storage paths.</li>
  <li><code>tasks/cad_tasks.py</code>: Houses the Celery background task (<code>run_cad_pipeline</code>) that instantiates the LangGraph pipeline, manages state updates, and logs live node telemetry.</li>
  <li><code>utils/llm.py</code>: Factory module managing LLM client connections. Features multi-key rotation, cooldown timers for rate-limits, and Cloudflare WAF bypass headers.</li>
</ul>

<h3>Agents & LangGraph Pipeline (`backend/agents/`)</h3>
<ul>
  <li><code>graph.py</code>: <strong>The Pipeline Graph.</strong> Compiles all agent nodes into an executable LangGraph <code>StateGraph</code>, defining conditional routes for assemblies, feature planning, and repair loops.</li>
  <li><code>state.py</code>: The shared state definition (<code>AgentState</code>) containing prompt text, images, CADIR tree, validation errors, build steps, and engineering outputs.</li>
  <li><code>input_classifier.py</code>: First node in the graph. Classifies input as text vs. multimodal image, and new part generation vs. parametric modification.</li>
  <li><code>supervisor.py</code>: Global orchestrator that enriches the context with domain-specific design rules and retrieves few-shot examples from historical CAD datasets.</li>
  <li><code>design_planner.py</code>: Decides whether the requested geometry represents a single monolithic component or a multi-part mechanical assembly.</li>
  <li><code>complexity_classifier.py</code>: Evaluates structural complexity. Simple parts go directly to single-pass design; complex parts are routed to the feature planner.</li>
  <li><code>feature_planner.py</code>: Decomposes complex parts into a chronological sequence of features (Base Body &rarr; Bosses &rarr; Cutouts &rarr; Holes &rarr; Fillets).</li>
  <li><code>incremental_design_agent.py</code>: Loops sequentially over the feature plan, synthesizing one feature at a time and merging it into the global CADIR tree.</li>
  <li><code>design_agent.py</code>: Single-pass synthesizer generating complete CADIR JSON for standard mechanical components.</li>
  <li><code>assembly_nodes.py</code>: Handles multi-component assemblies, generating spatial transforms, mates (coaxial, coincident), and clearance verifications.</li>
  <li><code>validator_nodes.py</code>: Intermediate bridge nodes invoking the CADIR schema validator, code interpreter, CAD executor, and physical geometry checker.</li>
  <li><code>cadir_repair_agent.py</code>: <strong>The Self-Healing Engine.</strong> When syntax or physical validation fails, this node analyzes the compiler error and patches the CADIR tree.</li>
  <li><code>downstream_nodes.py</code>: Contains the 6 downstream engineering analysis agents:
    <ul>
      <li><code>dfm_agent</code>: Flags injection molding draft angles, minimum wall thicknesses, and CNC cutter accessibility.</li>
      <li><code>engineering_agent</code>: Identifies structural load paths, material properties, and stress concentration zones.</li>
      <li><code>cost_agent</code>: Calculates raw material stock volume, bounding box billet mass, and machining cycle times.</li>
      <li><code>safety_agent</code>: Evaluates Factor of Safety (FoS) based on standard yield stresses and mechanical failure modes.</li>
      <li><code>alternatives_agent</code>: Suggests design trade-offs (e.g., sheet metal vs. casting, lightweight pocketing).</li>
      <li><code>cam_agent</code> / <code>doc_agent</code>: Details CNC milling setups, tool orientations, and generates manufacturing BOM documentation.</li>
    </ul>
  </li>
</ul>

<h3>CAD Kernel & CADIR Engine (`backend/cad/`)</h3>
<ul>
  <li><code>cadir/schema.py</code>: Strict Pydantic v2 schemas defining 2D sketch primitives, 3D operations, fillets, counterbores, spur gears, springs, and document roots.</li>
  <li><code>cadir/interpreter.py</code>: <strong>The Compiler.</strong> Translates CADIR JSON into deterministic, clean <code>build123d</code> Python code.</li>
  <li><code>cadir/validator.py</code>: Pre-flight validator checking for circular feature references, negative dimensions, or unclosed sketch boundaries.</li>
  <li><code>executor.py</code>: Executes generated code inside a sandboxed sub-process with timeouts, extracting B-Rep geometry and exporting STEP, STL, and GLB files.</li>
  <li><code>validator.py</code>: Verifies geometric physical sanity (volume &gt; 0, manifold solid check, bounding box checks).</li>
</ul>

<h3>Database (`backend/db/`)</h3>
<ul>
  <li><code>models.py</code>: SQLAlchemy relational models (<code>Session</code>, <code>Design</code>) storing prompts, multimodal images, CADIR trees, file paths, and reports.</li>
  <li><code>crud.py</code>: Database helper functions for creating, updating, and querying design records.</li>
  <li><code>migrate.py</code>: Idempotent migration script ensuring database tables automatically update with new columns (e.g., <code>image_data_b64</code>) on startup.</li>
</ul>

<h3>Frontend (`frontend/src/`)</h3>
<ul>
  <li><code>app/page.tsx</code>: Main workstation layout component.</li>
  <li><code>components/Workstation.tsx</code>: Core UI layout dividing the screen into Chat, 3D Viewport, Feature Tree, and Inspection panels.</li>
  <li><code>components/ViewerCanvas.tsx</code>: Interactive Three.js WebGL canvas with orbit controls and 100% offline procedural 3-point studio lighting.</li>
  <li><code>components/ChatPanel.tsx</code>: Multimodal chat UI supporting drag-and-drop image uploads, thumbnail preview ribbons, and prompt streaming.</li>
  <li><code>components/FeatureTree.tsx</code>: Chronological tree widget displaying parametric CAD operations with active/suppressed status.</li>
  <li><code>components/ExportPanel.tsx</code>: One-click export center for downloading production STEP, 3D-printable STL, and WebGL GLB files.</li>
  <li><code>components/AgentLog.tsx</code>: Real-time telemetry inspector streaming agent execution states, DFM flags, and CAM recommendations.</li>
</ul>

<h3>Evaluation & Benchmarking (`eval/`)</h3>
<ul>
  <li><code>build_golden_set.py</code>: Automated tool that extracts ground-truth geometric measurements (volumes, bounding boxes, hole counts) from raw STEP/STL models.</li>
  <li><code>run_eval.py</code>: Benchmarking runner that executes the CAD generation pipeline against test sets and records accuracy scores.</li>
  <li><code>metrics/shape.py</code>: Mathematical implementations of Chamfer Distance, Directed Hausdorff Distance, and 3D Voxel/Mesh IoU.</li>
  <li><code>metrics/dimensions.py</code>: Evaluates bounding box dimensional accuracy and critical engineering feature tolerances.</li>
  <li><code>metrics/positioning.py</code>: Validates Center of Mass (CoM) alignment and principal moments of inertia.</li>
</ul>

<div class="page-break"></div>

<!-- SECTION 4 -->
<h2>4. Project Evolution & Progression History</h2>
<p>
  The project evolved through a series of demanding real-world engineering hurdles. Below is the chronological progression from initial setup to production readiness:
</p>

<div class="meta-grid">
  <div class="meta-item">
    <div class="meta-label">Phase 1: Environment & Ports</div>
    <div class="meta-value">Resolved Windows Socket Permissions (WinError 10013) & MinIO Fallbacks</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Phase 2: Windows Python Virtualenv</div>
    <div class="meta-value">Bypassed OneDrive DLL Initialization Failures for OpenSSL & C-Extensions</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Phase 3: Celery Task Architecture</div>
    <div class="meta-value">Fixed Worker Signature Shifts & Stale Task Execution Traps</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Phase 4: LLM Key Pools & Cloudflare</div>
    <div class="meta-value">Bypassed Cloudflare Anti-Bot WAF & Upgraded Deprecated Gemini Models</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Phase 5: 3D Viewport Offline Stability</div>
    <div class="meta-value">Eliminated External GitHub CDN HDRs; Built Procedural Studio Rig</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Phase 6: Full-Stack Multimodal Support</div>
    <div class="meta-value">Added Drag-and-Drop Image Ingestion, DB Schema Auto-Migration & Vision Routing</div>
  </div>
</div>

<h3>Noteworthy Problems Faced & Technical Solutions</h3>

<div class="qa-card">
  <div class="qa-question">Problem 1: Celery Worker Task Signature Mismatch (`TypeError: takes 3 positional arguments but 4 were given`)</div>
  <div class="qa-answer">
    <strong>Root Cause:</strong> When a task is marked with <code>@celery_app.task(bind=True)</code>, Celery automatically injects the running task instance (<code>self</code>) as the first positional argument. However, when the backend falls back to running tasks synchronously (e.g., if Redis is unreachable), <code>self</code> is not passed. Additionally, a stale background Celery process had retained outdated function bytecode in memory.<br>
    <strong>Solution:</strong> We implemented defensive argument unpacking in <code>tasks/cad_tasks.py</code> that checks <code>isinstance(args[0], Task)</code> and shifts parameters dynamically. Stale worker processes were terminated using process tree pruning.
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Problem 2: Groq API Connection Drops & 403 Forbidden Errors</div>
  <div class="qa-answer">
    <strong>Root Cause:</strong> The Groq cloud endpoint is guarded by Cloudflare WAF. Standard Python HTTP clients (like default <code>httpx</code> or <code>urllib</code>) do not send standard browser headers, triggering Cloudflare anti-bot bot-management heuristics and causing silent TCP socket termination.<br>
    <strong>Solution:</strong> In <code>utils/llm.py</code>, we explicitly passed <code>default_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."}</code> to <code>ChatGroq</code>. Generation latency immediately stabilized at 1.2&ndash;1.8 seconds with zero dropouts.
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Problem 3: Windows Virtualenv OpenSSL DLL Failure (`ImportError: DLL load failed while importing _ssl`)</div>
  <div class="qa-answer">
    <strong>Root Cause:</strong> On Windows systems where project folders are synced with Microsoft OneDrive, the virtual environment launcher stub (<code>python.exe</code>) fails to resolve dynamic links for C-extensions (<code>_ssl.pyd</code>, <code>_ctypes.pyd</code>), preventing FastAPI from starting.<br>
    <strong>Solution:</strong> In <code>run.py</code>, we built an automatic Python probing function. It tests the venv for working <code>_ssl</code>; if it fails, it resolves the system's clean host Python 3.12 interpreter while mounting <code>backend/.venv/Lib/site-packages</code> into <code>sys.path</code>, preserving all installed dependencies without crashing.
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Problem 4: 3D Viewport Crashing on Restricted Networks</div>
  <div class="qa-answer">
    <strong>Root Cause:</strong> The Three.js canvas used <code>&lt;Environment preset="city" /&gt;</code> from <code>@react-three/drei</code>, which attempts to fetch a 1.2MB HDR environment file over public GitHub CDN. In offline environments or behind enterprise firewalls, this threw an unhandled network error, leaving the 3D viewport blank.<br>
    <strong>Solution:</strong> We eliminated the external HDR dependency and replaced it with an offline procedural lighting system inside <code>ViewerCanvas.tsx</code>: an ambient hemisphere light plus a 3-point studio lighting rig (key, fill, and rim lights).
  </div>
</div>

<div class="page-break"></div>

<!-- SECTION 5 -->
<h2>5. LangGraph & LangChain: Core Principles & State Machine Flow</h2>

<p>
  Understanding why and how LangGraph is used is critical for technical interviews.
</p>

<h3>Why LangGraph Instead of Standard Chains or Other Agent Frameworks?</h3>
<ul>
  <li><strong>Cycles & Iteration:</strong> Standard LangChain chains (LCEL) are Directed Acyclic Graphs (DAGs) &mdash; they only move forward. CAD modeling requires <em>cycles</em>: if a geometry verification test fails, the state must loop back to the repair agent and re-execute. LangGraph natively supports cyclical graphs.</li>
  <li><strong>Single Typed State Machine:</strong> Unlike conversational multi-agent frameworks (e.g., AutoGen, CrewAI) where agents exchange unstructured English text, LangGraph operates on a single, strictly-typed state dictionary (<code>AgentState</code>). Each node is a pure function that updates state variables deterministically.</li>
  <li><strong>Fine-Grained Checkpointing:</strong> If a downstream node (like cost estimation) fails, the system does not need to re-run expensive 3D CAD kernel calculations &mdash; it can resume from the last valid checkpoint.</li>
</ul>

<pre>
┌────────────────────────────────────────────────────────────────────────┐
│                     THE LANGGRAPH TOPOLOGY IN GRAPH.PY                 │
│                                                                        │
│  [input_classifier] ──> [supervisor] ──> [design_planner]              │
│                                                 │                      │
│                      ┌──────────────────────────┴──────────────────┐   │
│                      ▼ (is_assembly = True)                        ▼   │
│            [assembly_generator]                        [complexity]    │
│                      │                                  ┌────┴─────┐   │
│                      ▼                                  ▼          ▼   │
│            [assembly_executor]                  [feature_plan]  [design]
│                      │                                  │          │   │
│                      ▼                                  ▼          │   │
│            [assembly_validator]                  [incremental]     │   │
│                      │                                  │          │   │
│                      │                                  └────┬─────┘   │
│                      │                                       ▼         │
│                      │       ┌──────────────────────> [cadir_validator]│
│                      │       │ (Self-Healing Loop)           │ (Valid) │
│                      │       │                               ▼         │
│                      │       │                         [interpreter]   │
│                      │       │                               │         │
│                      │       │                               ▼         │
│                      │       │                         [cad_executor]  │
│                      │       │                               │         │
│                      │       │                               ▼         │
│                      │       └──────────────────── [geometry_validator]│
│                      │                                       │ (Valid) │
│                      └───────────────────┬───────────────────┘         │
│                                          ▼                             │
│  [dfm_agent] ──> [engineering_agent] ──> [cost_agent] ──> [safety] ──> [cam/doc]
└────────────────────────────────────────────────────────────────────────┘
</pre>

<div class="page-break"></div>

<!-- SECTION 6 -->
<h2>6. Mechanical Engineering Considerations & Domain Principles</h2>
<p>
  Senior engineering interviewers will probe your mechanical domain knowledge. Here are the foundational principles implemented in the workstation:
</p>

<h3>1. Boundary Representation (B-Rep) vs. Polygonal Meshes</h3>
<ul>
  <li><strong>B-Rep (STEP / IGES):</strong> Stores mathematical, exact topological primitives: Vertices, Edges, Curves (lines, circles, B-splines), Faces (planar, cylindrical, spherical, NURBS), Shells, and Solids. A cylindrical hole in STEP is mathematically exact ($x^2 + y^2 = r^2$) and can be recognized by CNC CAM software for drilling toolpaths.</li>
  <li><strong>Polygonal Mesh (STL / OBJ / GLB):</strong> Represents surfaces as flat triangular facets. Curves are approximated by chords, losing dimensional accuracy. Meshes cannot be cleanly edited, dimensioned, or checked for GD&T tolerances. Our system treats GLB purely as a visualization artifact while keeping STEP as the authoritative master CAD model.</li>
</ul>

<h3>2. DFM (Design for Manufacturing) Rules Enforced in the System</h3>
<ul>
  <li><strong>Internal Corner Radii:</strong> CNC milling tools are rotating cylinders and cannot create sharp $90^\circ$ inside vertical corners. The agent flags missing internal corner fillets ($R \ge \text{tool diameter}/2$).</li>
  <li><strong>Draft Angles for Molding/Casting:</strong> Vertical walls must possess a $1^\circ &ndash; 3^\circ$ draft angle to allow ejection from the mold cavity without surface tearing.</li>
  <li><strong>Minimum Wall Thickness:</strong> Prevents short-shot defects in plastic injection molding and structural buckling during subtractive machining.</li>
  <li><strong>Standard Fastener Pitches:</strong> Threads must follow standard metric/unified series (e.g., M6x1.0, M10x1.5), not arbitrary floating-point diameters.</li>
</ul>

<h3>3. Topological & Geometric Validation Invariants</h3>
<div class="callout callout-warning">
  <div class="callout-title">Euler-Poincaré Formula Verification</div>
  <p>
    For any closed, 2-manifold orientable polyhedral solid, the Euler-Poincaré formula must hold:
    <br>
    $$\mathbf{V - E + F - (H - 2P) = 2(S - G)}$$
    Where $V$ = Vertices, $E$ = Edges, $F$ = Faces, $H$ = Inner hole loops in faces, $P$ = Passages (through-holes), $S$ = Shells, and $G$ = Genus (torus topology). If the OpenCASCADE B-Rep shape violates this condition, the model is topologically non-manifold and will fail boolean operations in downstream CAD software.
  </p>
</div>

<div class="page-break"></div>

<!-- SECTION 7 -->
<h2>7. Tricky Technical Questionnaire & Answers (For Mechanical Faculty & Senior Interviewers)</h2>

<div class="qa-card">
  <div class="qa-question">Q1: "Why did you invent CADIR? Why not have the LLM output raw CadQuery or OpenCASCADE Python code directly?"</div>
  <div class="qa-answer">
    <strong>Answer:</strong> Direct code generation fails in over 65% of test cases due to three structural factors:
    <ol>
      <li><strong>API Surface Area & Hallucination:</strong> OpenCASCADE has thousands of methods, and CadQuery has complex fluent selector chaining (e.g., <code>.faces('&gt;Z').edges('&lt;X')</code>). LLMs frequently hallucinate selectors or use deprecated methods.</li>
      <li><strong>Selector Instability:</strong> If an LLM selects edges by ordinal index (e.g., <code>.edges()[4]</code>), minor changes in previous operations alter edge numbering, resulting in fillets failing or cutting the wrong faces.</li>
      <li><strong>Security & Determinism:</strong> Executing unconstrained, arbitrary Python code generated by an AI model is an enterprise Remote Code Execution (RCE) vulnerability.</li>
    </ol>
    CADIR solves this by acting as a strongly-typed intermediate bytecode. The LLM only generates validated JSON schemas containing geometric parameters. Our deterministic interpreter maps this schema into tested, rock-solid <code>build123d</code> primitives.
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Q2: "How do you evaluate whether the generated CAD model matches the ground truth? You can't just do text comparison on code."</div>
  <div class="qa-answer">
    <strong>Answer:</strong> Text comparison is meaningless in CAD because there are infinite distinct feature sequences that yield the exact same physical shape (e.g., extruding a cylinder vs. revolving a rectangle). We evaluate on <strong>raw 3D CAD geometry</strong> across three metric pillars:
    <ul>
      <li><strong>Shape Topology:</strong>
        <ul>
          <li><strong>Chamfer Distance (CD):</strong> Uniformly samples 10,000 points across both B-Rep surfaces and measures bidirectional nearest-neighbor distance.</li>
          <li><strong>Directed Hausdorff Distance:</strong> Identifies the maximum outlier surface deviation (detecting missing bosses or incorrect cuts).</li>
          <li><strong>3D Voxel IoU:</strong> Measures volumetric overlap ($V_A \cap V_B / V_A \cup V_B$) on a discretized $128^3$ voxel grid.</li>
        </ul>
      </li>
      <li><strong>Dimensional Accuracy:</strong> Extracts the minimum bounding envelope ($L \times W \times H$) directly from the B-Rep vertices and calculates percentage error against ground truth.</li>
      <li><strong>Positioning:</strong> Compares the Center of Mass (CoM) coordinates and principal moments of inertia.</li>
    </ul>
    Ground truth is always calculated from the raw CAD geometry of the golden dataset, never inferred from prompt text.
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Q3: "What happens if OpenCASCADE produces a non-manifold body or a self-intersection? How does the pipeline detect and handle it?"</div>
  <div class="qa-answer">
    <strong>Answer:</strong> In our pipeline, the <code>cad_executor</code> node passes the shape to <code>geometry_validator</code>, which runs three checks:
    <ol>
      <li><strong>Volume and Surface Area:</strong> Verifies that $\text{Volume} > 10^{-6}\text{ mm}^3$ and $\text{Area} > 10^{-6}\text{ mm}^2$ to catch degenerate null solids.</li>
      <li><strong>B-Rep Manifold Check:</strong> Invokes OpenCASCADE's <code>BRepCheck_Analyzer</code> to confirm that every edge is shared by exactly two faces (2-manifold condition) and verifies outward-pointing face normal consistency.</li>
      <li><strong>Euler-Poincaré Characteristic:</strong> Validates polyhedral topology invariants.</li>
    </ol>
    If any check fails, <code>geometry_validator</code> sets <code>geometry_valid = False</code>, captures the exact OpenCASCADE topological fault, and routes execution to the <code>cadir_repair_agent</code>. The repair agent modifies parameters (for instance, reducing an overly large fillet radius that would consume an adjacent face) and re-executes.
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Q4: "How do you handle multi-part assemblies and mating constraints (e.g., a shaft inside a bearing)?"</div>
  <div class="qa-answer">
    <strong>Answer:</strong> When <code>design_planner</code> detects an assembly, the graph routes to <code>assembly_generator</code>. An assembly in CADIR is defined by:
    <ul>
      <li>A list of individual component CADIR documents.</li>
      <li>A coordinate transformation matrix (Translation $\vec{T}$, Rotation $\vec{R}$) for each component relative to world origin.</li>
      <li>Explicit mating constraints (Coaxial, Coincident, Offset, Clearance).</li>
    </ul>
    During <code>assembly_validator</code>, the engine performs pairwise boolean intersection checks ($\text{Body}_A \cap \text{Body}_B$). If the intersection volume is greater than zero, an interference/collision fault is flagged. For clearance fits, the validator ensures the required tolerance envelope is preserved.
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Q5: "LLMs struggle with 3D spatial reasoning. How does your vision analyzer extract 3D dimensions from a 2D image upload?"</div>
  <div class="qa-answer">
    <strong>Answer:</strong> A single 2D image cannot uniquely resolve 3D geometry without domain-specific priors. Our vision pipeline uses a 4-step approach:
    <ol>
      <li><strong>Projection Classification:</strong> Classifies whether the image is an isometric view, orthographic technical drawing (Front, Top, Right), or perspective photograph.</li>
      <li><strong>OCR Dimension Extraction:</strong> Detects dimension leader lines, numerical callouts (e.g., '$\varnothing 25$', '$\text{R}5$', '$50\pm0.1$'), and thread annotations.</li>
      <li><strong>Parametric Family Fitting:</strong> Instead of noisy point-cloud reconstruction, the agent matches the silhouette to known mechanical templates (family recipes like flanges, brackets, stepped shafts, gearboxes) and binds numerical callouts to template parameters.</li>
      <li><strong>Aspect Ratio Sanity Checking:</strong> Compares predicted dimensional ratios against visual pixel aspect ratios.</li>
    </ol>
  </div>
</div>

<div class="qa-card">
  <div class="qa-question">Q6: "If a user requests a part with a thread (like an M10 bolt), do you model the actual helical thread coil or a cosmetic cylinder? Why?"</div>
  <div class="qa-answer">
    <strong>Answer:</strong> In production CAD (SolidWorks, Inventor, Siemens NX), modeling real physical helical threads for every fastener is bad practice because a true helical B-Rep surface creates thousands of complex NURBS surface patches that dramatically inflate file size, slow down viewport rendering, and cause boolean failures in downstream assemblies.<br>
    Our CADIR schema supports both modes via the <code>thread_type</code> parameter:
    <ul>
      <li>By default, it generates a <strong>schematic/cosmetic thread representation</strong> (nominal minor/major cylinder with standard chamfered lead-in) and writes standard thread callouts (e.g., 'M10x1.5-6g') into the manufacturing drawing documentation.</li>
      <li>If the user explicitly specifies 3D printing (additive manufacturing), the interpreter executes a true helical sweep using standard ISO metric $60^\circ$ thread profile equations.</li>
    </ul>
  </div>
</div>

<div style="text-align: center; color: #94a3b8; font-size: 8.5pt; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
  CAD AI Workstation &bull; Industrial AI & Mechanical Engineering System Dossier &bull; Generated for Technical Interview Defense
</div>

</body>
</html>
"""

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_file = os.path.join(root_dir, "CAD_AI_Workstation_Complete_Project_Synopsis.html")
    pdf_file = os.path.join(root_dir, "CAD_AI_Workstation_Complete_Project_Synopsis.pdf")
    
    print(f"Writing HTML to: {html_file}")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(build_html_content())
        
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    browser_bin = chrome_path if os.path.exists(chrome_path) else edge_path
    if not os.path.exists(browser_bin):
        print(f"Error: Neither Chrome nor Edge found at expected paths.")
        sys.exit(1)
        
    print(f"Generating PDF with headless browser: {browser_bin}")
    cmd = [
        browser_bin,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_file}",
        html_file
    ]
    subprocess.run(cmd, check=True)
    
    if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 1000:
        print(f"SUCCESS: Generated PDF at {pdf_file} (Size: {os.path.getsize(pdf_file)} bytes)")
    else:
        print(f"ERROR: PDF was not generated properly.")
        sys.exit(1)

if __name__ == "__main__":
    main()
