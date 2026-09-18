from __future__ import annotations
import os
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from stage1.atlas import StudyGraph, Atlas, DataNormalizer, ProtocolEngine
from starter.schemas import Question, Answer, RecordRef

app = FastAPI(title="Study Sentinel - ATLAS Dashboard", version="1.0.0")

# Initialize graph and agent
DATA_DIR = os.path.join(os.path.dirname(__file__), "hackathon-data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = "hackathon-data"

study_graph = StudyGraph(data_dir=DATA_DIR)
study_graph.build(cut=12)
atlas_agent = Atlas(study_graph)


class QueryRequest(BaseModel):
    question: str
    type: Optional[str] = None
    cut: Optional[int] = None
    usubjid: Optional[str] = None
    visit: Optional[str] = None


@app.get("/api/stats")
def get_stats(cut: Optional[int] = None):
    """Returns graph statistics, optionally rebuilding for a specific cut."""
    if cut is not None and isinstance(cut, int) and cut != study_graph.cut:
        stats = study_graph.build(cut=cut)
        return stats
    return study_graph.stats


@app.get("/api/subjects")
def get_subjects():
    """Returns all enrolled subject IDs."""
    return sorted(list(study_graph.subjects.keys()))


@app.get("/api/patient/{usubjid}")
def get_patient(usubjid: str):
    """Returns Patient 360 profile in O(1) time."""
    patient = study_graph.patient360(usubjid)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Subject {usubjid} not found")
    return patient


@app.post("/api/ask")
def ask_question(req: QueryRequest):
    """Runs a query through Atlas and returns the Answer with cited evidence."""
    active_cut = req.cut if req.cut is not None else study_graph.cut
    if req.cut is not None and req.cut != study_graph.cut:
        study_graph.build(cut=req.cut)

    q = Question(
        question=req.question,
        type=req.type,
        cut=active_cut,
        usubjid=req.usubjid,
        visit=req.visit,
    )
    ans = atlas_agent.answer(q)
    return ans.model_dump()


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Study Sentinel — ATLAS Phase III Clinical Intelligence</title>
  <!-- Bootstrap 5 CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <!-- Tailwind CSS with prefix tw- -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      prefix: 'tw-',
      theme: {
        extend: {
          colors: {
            brand: '#0d6efd',
            darknav: '#0f172a',
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
    .kpi-card { border-radius: 12px; border: 1px solid #e2e8f0; transition: transform 0.2s, box-shadow 0.2s; }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.07); }
    .ref-badge { font-family: monospace; font-size: 0.8rem; cursor: pointer; transition: all 0.15s; }
    .ref-badge:hover { filter: brightness(0.9); transform: scale(1.03); }
    .table-sm th, .table-sm td { font-size: 0.85rem; vertical-align: middle; }
  </style>
</head>
<body class="tw-min-h-screen tw-flex tw-flex-col">

  <!-- Navbar -->
  <nav class="navbar navbar-dark bg-dark px-4 py-3 tw-shadow-md">
    <div class="container-fluid d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center gap-3">
        <i class="bi bi-shield-check text-primary fs-3"></i>
        <div>
          <span class="navbar-brand mb-0 h1 fw-bold tw-tracking-wide">Study Sentinel — ATLAS</span>
          <span class="badge bg-primary-subtle text-primary border border-primary-subtle ms-2">Stage 1</span>
        </div>
      </div>
      <div class="d-flex align-items-center gap-3">
        <div class="d-flex align-items-center gap-2 bg-secondary bg-opacity-25 px-3 py-1 rounded-pill">
          <span class="text-white-50 small">Active Cut:</span>
          <select id="cutSelector" class="form-select form-select-sm bg-dark text-white border-secondary" style="width: auto;" onchange="onCutChange()">
            <option value="1">Cut 1 (v1, ±7d)</option>
            <option value="4">Cut 4 (v1, ±7d)</option>
            <option value="5">Cut 5 (v2, ±3d)</option>
            <option value="8">Cut 8 (v2, ±3d)</option>
            <option value="9">Cut 9 (v3, ±3d)</option>
            <option value="12" selected>Cut 12 (v3, Final)</option>
          </select>
        </div>
        <span id="activeProtocolBadge" class="badge bg-info text-dark">Protocol v3</span>
      </div>
    </div>
  </nav>

  <!-- Container -->
  <div class="container-fluid px-4 py-4 tw-flex-1">

    <!-- KPI Cards Row -->
    <div class="row g-3 mb-4">
      <div class="col-md-3">
        <div class="card kpi-card bg-white p-3 shadow-sm">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <div class="text-muted small fw-semibold text-uppercase">Total Graph Nodes</div>
              <div class="h3 fw-bold text-dark mb-0 mt-1" id="kpiNodes">—</div>
            </div>
            <div class="bg-primary bg-opacity-10 text-primary p-3 rounded-3">
              <i class="bi bi-diagram-3 fs-3"></i>
            </div>
          </div>
          <div class="small text-muted mt-2"><i class="bi bi-check-circle text-success me-1"></i>Subjects, sites & domain records</div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card kpi-card bg-white p-3 shadow-sm">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <div class="text-muted small fw-semibold text-uppercase">Total Graph Edges</div>
              <div class="h3 fw-bold text-dark mb-0 mt-1" id="kpiEdges">—</div>
            </div>
            <div class="bg-info bg-opacity-10 text-info p-3 rounded-3">
              <i class="bi bi-bezier2 fs-3"></i>
            </div>
          </div>
          <div class="small text-muted mt-2"><i class="bi bi-link-45deg text-info me-1"></i>Enrolled & event relationships</div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card kpi-card bg-white p-3 shadow-sm">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <div class="text-muted small fw-semibold text-uppercase">Enrolled Subjects</div>
              <div class="h3 fw-bold text-dark mb-0 mt-1" id="kpiSubjects">—</div>
            </div>
            <div class="bg-success bg-opacity-10 text-success p-3 rounded-3">
              <i class="bi bi-people fs-3"></i>
            </div>
          </div>
          <div class="small text-muted mt-2"><i class="bi bi-building text-success me-1"></i>Across 12 trial sites</div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card kpi-card bg-white p-3 shadow-sm">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <div class="text-muted small fw-semibold text-uppercase">Graph Build Latency</div>
              <div class="h3 fw-bold text-dark mb-0 mt-1" id="kpiLatency">—</div>
            </div>
            <div class="bg-warning bg-opacity-10 text-warning p-3 rounded-3">
              <i class="bi bi-stopwatch fs-3"></i>
            </div>
          </div>
          <div class="small text-muted mt-2"><i class="bi bi-lightning-charge text-warning me-1"></i>High-throughput memory build</div>
        </div>
      </div>
    </div>

    <!-- Main 2-Column Section -->
    <div class="row g-4">

      <!-- Left Panel: Reviewer Query Console -->
      <div class="col-lg-6">
        <div class="card shadow-sm h-100 border-0">
          <div class="card-header bg-white py-3 border-bottom d-flex justify-content-between align-items-center">
            <h5 class="mb-0 fw-bold text-dark d-flex align-items-center gap-2">
              <i class="bi bi-terminal-fill text-primary"></i> Reviewer Query Console
            </h5>
            <span class="badge bg-secondary-subtle text-secondary">QA Engine</span>
          </div>
          <div class="card-body p-4 d-flex flex-column">

            <!-- Presets -->
            <div class="mb-3">
              <label class="form-label text-muted small fw-bold text-uppercase">Pre-Set Regulatory & Safety Queries</label>
              <div class="d-flex flex-wrap gap-2">
                <button class="btn btn-outline-danger btn-sm" onclick="runPreset('hys_law')">
                  <i class="bi bi-exclamation-triangle-fill me-1"></i> Hy's Law Finding
                </button>
                <button class="btn btn-outline-warning btn-sm" onclick="runPreset('prohibited_meds')">
                  <i class="bi bi-capsule-pill me-1"></i> Prohibited Meds
                </button>
                <button class="btn btn-outline-primary btn-sm" onclick="runPreset('discontinuations')">
                  <i class="bi bi-box-arrow-right me-1"></i> AE Discontinuations
                </button>
                <button class="btn btn-outline-dark btn-sm" onclick="runPreset('trap')">
                  <i class="bi bi-shield-slash me-1"></i> Trap: Site S01 Wrong Dose
                </button>
              </div>
            </div>

            <!-- Free Text Query Input -->
            <div class="mb-3">
              <label class="form-label text-muted small fw-bold text-uppercase">Custom Natural Query</label>
              <div class="input-group">
                <input type="text" id="customQueryInput" class="form-control" placeholder="Ask a study finding or audit question...">
                <button class="btn btn-primary" onclick="runCustomQuery()">
                  <i class="bi bi-send-fill me-1"></i> Execute
                </button>
              </div>
            </div>

            <!-- Output Box -->
            <div class="card bg-light border-0 p-3 mt-2 tw-flex-1 d-flex flex-column" style="min-height: 280px;">
              <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                <span class="fw-bold small text-secondary">Console Result</span>
                <span id="confidenceBadge" class="badge bg-secondary">Confidence: —</span>
              </div>

              <!-- Reasoning / Status -->
              <div id="queryOutputReasoning" class="text-dark small mb-3">
                Select a preset question or submit a custom query to evaluate findings across data cuts.
              </div>

              <!-- Main Answer Display -->
              <div class="mb-3">
                <div class="text-muted small fw-semibold text-uppercase mb-1">Answer Value</div>
                <div id="queryOutputAnswer" class="p-2 bg-white rounded border small font-monospace text-break" style="max-height: 100px; overflow-y: auto;">
                  None
                </div>
              </div>

              <!-- Evidence Panel -->
              <div class="tw-flex-1">
                <div class="text-muted small fw-semibold text-uppercase mb-1 d-flex justify-content-between">
                  <span>Cited Record Evidence (<span id="evidenceCount">0</span>)</span>
                  <span class="tw-text-xs text-muted">Click badge to view Patient 360</span>
                </div>
                <div id="queryOutputEvidence" class="d-flex flex-wrap gap-1 p-2 bg-white rounded border" style="max-height: 130px; overflow-y: auto;">
                  <span class="text-muted small">No evidence cited.</span>
                </div>
              </div>

            </div>

          </div>
        </div>
      </div>

      <!-- Right Panel: Patient 360 Inspector -->
      <div class="col-lg-6">
        <div class="card shadow-sm h-100 border-0">
          <div class="card-header bg-white py-3 border-bottom d-flex justify-content-between align-items-center">
            <h5 class="mb-0 fw-bold text-dark d-flex align-items-center gap-2">
              <i class="bi bi-person-bounding-box text-success"></i> Patient 360 Inspector
            </h5>
            <span class="badge bg-success-subtle text-success border border-success-subtle">O(1) Hash Map</span>
          </div>
          <div class="card-body p-4">

            <!-- Search Bar -->
            <div class="mb-3">
              <label class="form-label text-muted small fw-bold text-uppercase">Select or Search Subject (USUBJID)</label>
              <div class="input-group">
                <input type="text" id="patientSearchInput" list="subjectList" class="form-control font-monospace" placeholder="e.g. 042-S07-001" onchange="fetchPatient(this.value)">
                <datalist id="subjectList"></datalist>
                <button class="btn btn-outline-secondary" onclick="fetchPatient(document.getElementById('patientSearchInput').value)">
                  <i class="bi bi-search"></i> Inspect
                </button>
              </div>
            </div>

            <!-- Subject Demographics Card -->
            <div id="patientProfileCard" class="card bg-light border-0 p-3 mb-3 d-none">
              <div class="row g-2 small">
                <div class="col-4"><span class="text-muted">USUBJID:</span> <strong id="pUsubjid" class="font-monospace text-primary"></strong></div>
                <div class="col-4"><span class="text-muted">Arm:</span> <span id="pArm" class="badge bg-secondary"></span></div>
                <div class="col-4"><span class="text-muted">Site:</span> <strong id="pSite"></strong></div>
                <div class="col-4"><span class="text-muted">Age / Sex:</span> <span id="pDemog"></span></div>
                <div class="col-4"><span class="text-muted">Baseline:</span> <span id="pBaseline"></span></div>
                <div class="col-4"><span class="text-muted">Scr HbA1c:</span> <strong id="pHba1c"></strong>%</div>
              </div>
            </div>

            <!-- Domain Tabs -->
            <ul class="nav nav-tabs mb-3" id="patientTabs" role="tablist">
              <li class="nav-item" role="presentation">
                <button class="nav-link active py-1 px-3 small" id="labs-tab" data-bs-toggle="tab" data-bs-target="#labs-content" type="button">
                  Labs (LB) <span id="countLb" class="badge bg-light text-dark border">0</span>
                </button>
              </li>
              <li class="nav-item" role="presentation">
                <button class="nav-link py-1 px-3 small" id="ae-tab" data-bs-toggle="tab" data-bs-target="#ae-content" type="button">
                  Adverse Events (AE) <span id="countAe" class="badge bg-light text-dark border">0</span>
                </button>
              </li>
              <li class="nav-item" role="presentation">
                <button class="nav-link py-1 px-3 small" id="cm-tab" data-bs-toggle="tab" data-bs-target="#cm-content" type="button">
                  ConMeds (CM) <span id="countCm" class="badge bg-light text-dark border">0</span>
                </button>
              </li>
              <li class="nav-item" role="presentation">
                <button class="nav-link py-1 px-3 small" id="ex-tab" data-bs-toggle="tab" data-bs-target="#ex-content" type="button">
                  Dosing / Disp <span id="countEx" class="badge bg-light text-dark border">0</span>
                </button>
              </li>
            </ul>

            <!-- Tabs Content -->
            <div class="tab-content" id="patientTabsContent">

              <!-- Labs Tab -->
              <div class="tab-pane fade show active" id="labs-content">
                <div class="table-responsive" style="max-height: 240px; overflow-y: auto;">
                  <table class="table table-sm table-hover mb-0">
                    <thead class="table-light sticky-top">
                      <tr>
                        <th>Seq</th>
                        <th>Visit</th>
                        <th>Test</th>
                        <th>Value</th>
                        <th>Unit</th>
                        <th>Date</th>
                        <th>Alert</th>
                      </tr>
                    </thead>
                    <tbody id="labsTableBody">
                      <tr><td colspan="7" class="text-center text-muted py-3">Select a subject to view laboratory records.</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Adverse Events Tab -->
              <div class="tab-pane fade" id="ae-content">
                <div class="table-responsive" style="max-height: 240px; overflow-y: auto;">
                  <table class="table table-sm table-hover mb-0">
                    <thead class="table-light sticky-top">
                      <tr>
                        <th>Seq</th>
                        <th>Term</th>
                        <th>Severity</th>
                        <th>Serious (AESER)</th>
                        <th>Hosp (AESHOSP)</th>
                        <th>Onset Date</th>
                      </tr>
                    </thead>
                    <tbody id="aeTableBody">
                      <tr><td colspan="6" class="text-center text-muted py-3">Select a subject to view adverse events.</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Concomitant Meds Tab -->
              <div class="tab-pane fade" id="cm-content">
                <div class="table-responsive" style="max-height: 240px; overflow-y: auto;">
                  <table class="table table-sm table-hover mb-0">
                    <thead class="table-light sticky-top">
                      <tr>
                        <th>Seq</th>
                        <th>Treatment</th>
                        <th>Class</th>
                        <th>Indication</th>
                        <th>Dose</th>
                        <th>Start Date</th>
                      </tr>
                    </thead>
                    <tbody id="cmTableBody">
                      <tr><td colspan="6" class="text-center text-muted py-3">Select a subject to view concomitant medications.</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Dosing / Discontinuation Tab -->
              <div class="tab-pane fade" id="ex-content">
                <div class="table-responsive" style="max-height: 240px; overflow-y: auto;">
                  <table class="table table-sm table-hover mb-0">
                    <thead class="table-light sticky-top">
                      <tr>
                        <th>Domain</th>
                        <th>Seq</th>
                        <th>Visit / Term</th>
                        <th>Dose / Status</th>
                        <th>Date</th>
                      </tr>
                    </thead>
                    <tbody id="exTableBody">
                      <tr><td colspan="5" class="text-center text-muted py-3">Select a subject to view exposure & disposition.</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

            </div>

          </div>
        </div>
      </div>

    </div>

  </div>

  <!-- Bootstrap JS Bundle -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

  <!-- Dashboard Script -->
  <script>
    let currentCut = 12;

    async function initDashboard() {
      await fetchStats();
      await fetchSubjectsList();
      // Default to inspecting first Hy's Law candidate
      fetchPatient('042-S07-001');
    }

    async function fetchStats() {
      try {
        const res = await fetch(`/api/stats?cut=${currentCut}`);
        const data = await res.json();
        document.getElementById('kpiNodes').textContent = data.nodes.toLocaleString();
        document.getElementById('kpiEdges').textContent = data.edges.toLocaleString();
        document.getElementById('kpiSubjects').textContent = data.subjects.toLocaleString();
        document.getElementById('kpiLatency').textContent = `${data.ms} ms`;
        
        let pVer = 'Protocol v3';
        if (currentCut <= 4) pVer = 'Protocol v1 (±7d)';
        else if (currentCut <= 8) pVer = 'Protocol v2 (±3d)';
        document.getElementById('activeProtocolBadge').textContent = pVer;
      } catch (err) {
        console.error('Failed to load stats:', err);
      }
    }

    async function fetchSubjectsList() {
      try {
        const res = await fetch('/api/subjects');
        const subjects = await res.json();
        const dl = document.getElementById('subjectList');
        dl.innerHTML = '';
        subjects.forEach(s => {
          const opt = document.createElement('option');
          opt.value = s;
          dl.appendChild(opt);
        });
      } catch (err) {
        console.error('Failed to load subjects list:', err);
      }
    }

    async function onCutChange() {
      currentCut = parseInt(document.getElementById('cutSelector').value);
      await fetchStats();
      const currentPatient = document.getElementById('patientSearchInput').value;
      if (currentPatient) {
        fetchPatient(currentPatient);
      }
    }

    async function runPreset(type) {
      let payload = { cut: currentCut, type: type };
      if (type === 'hys_law') {
        payload.question = "Identify all potential Hy's Law candidate subjects and cite exact LB records.";
      } else if (type === 'prohibited_meds') {
        payload.question = "Identify subjects taking prohibited concomitant medications under the active protocol cut.";
      } else if (type === 'discontinuations') {
        payload.question = "Count subjects who discontinued study participation due to an adverse event.";
      } else if (type === 'trap') {
        payload.question = "Report all wrong doses and dosing errors at Site S01.";
      }
      document.getElementById('customQueryInput').value = payload.question;
      await executeQuery(payload);
    }

    async function runCustomQuery() {
      const q = document.getElementById('customQueryInput').value.trim();
      if (!q) return;
      await executeQuery({ question: q, cut: currentCut });
    }

    async function executeQuery(payload) {
      document.getElementById('queryOutputReasoning').innerHTML = '<span class="spinner-border spinner-border-sm text-primary me-2"></span>Evaluating knowledge graph...';
      try {
        const res = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        document.getElementById('confidenceBadge').textContent = `Confidence: ${(data.confidence * 100).toFixed(0)}%`;
        document.getElementById('confidenceBadge').className = data.confidence >= 0.9 ? 'badge bg-success' : 'badge bg-warning';
        document.getElementById('queryOutputReasoning').textContent = data.reasoning || 'Query complete.';
        document.getElementById('queryOutputAnswer').textContent = JSON.stringify(data.answer, null, 2);

        const evList = document.getElementById('queryOutputEvidence');
        evList.innerHTML = '';
        const evidence = data.evidence || [];
        document.getElementById('evidenceCount').textContent = evidence.length;

        if (evidence.length === 0) {
          evList.innerHTML = '<span class="text-muted small">No evidence records cited (none required).</span>';
        } else {
          evidence.forEach(ref => {
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary-subtle text-primary border border-primary-subtle ref-badge';
            badge.textContent = `${ref.domain} | ${ref.usubjid} | Seq ${ref.seq}`;
            badge.title = `Click to inspect subject ${ref.usubjid}`;
            badge.onclick = () => {
              document.getElementById('patientSearchInput').value = ref.usubjid;
              fetchPatient(ref.usubjid);
            };
            evList.appendChild(badge);
          });
        }
      } catch (err) {
        document.getElementById('queryOutputReasoning').innerHTML = `<span class="text-danger">Error executing query: ${err}</span>`;
      }
    }

    async function fetchPatient(usubjid) {
      if (!usubjid) return;
      try {
        const res = await fetch(`/api/patient/${encodeURIComponent(usubjid)}`);
        if (!res.ok) {
          alert(`Subject ${usubjid} not found.`);
          return;
        }
        const p = await res.json();
        renderPatient(p);
      } catch (err) {
        console.error('Failed to fetch patient:', err);
      }
    }

    function renderPatient(p) {
      document.getElementById('patientProfileCard').classList.remove('d-none');
      document.getElementById('pUsubjid').textContent = p.usubjid;
      document.getElementById('pArm').textContent = p.arm || 'Unknown';
      document.getElementById('pArm').className = p.arm === 'DRUG' ? 'badge bg-primary' : 'badge bg-secondary';
      document.getElementById('pSite').textContent = `${p.siteid} (${p.country})`;
      document.getElementById('pDemog').textContent = `${p.age} y / ${p.sex}`;
      document.getElementById('pBaseline').textContent = p.rfstdtc || '—';
      document.getElementById('pHba1c').textContent = p.scr_hba1c || '—';

      // Counts
      document.getElementById('countLb').textContent = p.lb ? p.lb.length : 0;
      document.getElementById('countAe').textContent = p.ae ? p.ae.length : 0;
      document.getElementById('countCm').textContent = p.cm ? p.cm.length : 0;
      document.getElementById('countEx').textContent = (p.ex ? p.ex.length : 0) + (p.ds ? p.ds.length : 0);

      // Render Labs
      const lbBody = document.getElementById('labsTableBody');
      lbBody.innerHTML = '';
      if (!p.lb || p.lb.length === 0) {
        lbBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-2">No lab records available.</td></tr>';
      } else {
        p.lb.forEach(r => {
          const tr = document.createElement('tr');
          let alertBadge = '<span class="badge bg-light text-muted">Normal</span>';
          if (r.uln && r.val) {
            if (['ALT', 'AST'].includes(r.testcd) && r.val > 3.0 * r.uln) {
              alertBadge = '<span class="badge bg-danger">ALT/AST > 3x ULN</span>';
            } else if (r.testcd === 'BILI' && r.val > 2.0 * r.uln) {
              alertBadge = '<span class="badge bg-danger">BILI > 2x ULN</span>';
            } else if (r.val > r.uln) {
              alertBadge = '<span class="badge bg-warning text-dark">> ULN</span>';
            }
          }
          const valDisplay = r.val !== null ? r.val.toFixed(2) : (r.raw_val || 'ND');
          tr.innerHTML = `
            <td>${r.seq}</td>
            <td><span class="badge bg-secondary-subtle text-secondary">${r.visit}</span></td>
            <td><strong>${r.testcd}</strong></td>
            <td>${valDisplay}</td>
            <td class="text-muted">${r.unit}</td>
            <td>${r.date || '—'}</td>
            <td>${alertBadge}</td>
          `;
          lbBody.appendChild(tr);
        });
      }

      // Render AE
      const aeBody = document.getElementById('aeTableBody');
      aeBody.innerHTML = '';
      if (!p.ae || p.ae.length === 0) {
        aeBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-2">No adverse events recorded.</td></tr>';
      } else {
        p.ae.forEach(r => {
          const tr = document.createElement('tr');
          const serBadge = r.serious ? '<span class="badge bg-danger">Yes</span>' : '<span class="badge bg-light text-muted">No</span>';
          const hospBadge = r.aeshosp === 'Y' ? '<span class="badge bg-warning text-dark">HOSPITAL</span>' : '<span class="badge bg-light text-muted">No</span>';
          tr.innerHTML = `
            <td>${r.seq}</td>
            <td><strong>${r.term}</strong></td>
            <td><span class="badge bg-secondary-subtle text-dark">${r.sev}</span></td>
            <td>${serBadge}</td>
            <td>${hospBadge}</td>
            <td>${r.stdtc || '—'}</td>
          `;
          aeBody.appendChild(tr);
        });
      }

      // Render CM
      const cmBody = document.getElementById('cmTableBody');
      cmBody.innerHTML = '';
      if (!p.cm || p.cm.length === 0) {
        cmBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-2">No concomitant medications recorded.</td></tr>';
      } else {
        p.cm.forEach(r => {
          const tr = document.createElement('tr');
          let flagProhib = '';
          const upperClas = (r.clas || '').toUpperCase();
          const upperTrt = (r.trt || '').toUpperCase();
          if (upperClas.includes('GLUCOCORTICOID') || upperTrt.includes('PREDNIS')) {
            flagProhib = '<span class="badge bg-danger ms-1">PROHIBITED (v1-v3)</span>';
          } else if (upperClas.includes('SULFONYLUREA') || upperTrt.includes('GLIBEN')) {
            flagProhib = '<span class="badge bg-warning text-dark ms-1">PROHIBITED (v3)</span>';
          }
          tr.innerHTML = `
            <td>${r.seq}</td>
            <td><strong>${r.trt}</strong> ${flagProhib}</td>
            <td>${r.clas}</td>
            <td>${r.indc || '—'}</td>
            <td>${r.dose !== null ? r.dose : '—'}</td>
            <td>${r.stdtc || '—'}</td>
          `;
          cmBody.appendChild(tr);
        });
      }

      // Render Dosing / Disposition
      const exBody = document.getElementById('exTableBody');
      exBody.innerHTML = '';
      let rows = [];
      (p.ex || []).forEach(r => {
        rows.push({
          dom: 'EX',
          seq: r.seq,
          term: r.visit,
          stat: `${r.dose} ${r.dosu}`,
          dt: r.stdtc
        });
      });
      (p.ds || []).forEach(r => {
        rows.push({
          dom: 'DS',
          seq: r.seq,
          term: r.term || r.decod,
          stat: r.decod,
          dt: r.stdtc
        });
      });

      if (rows.length === 0) {
        exBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-2">No exposure or disposition records.</td></tr>';
      } else {
        rows.forEach(r => {
          const tr = document.createElement('tr');
          const domBadge = r.dom === 'DS' ? '<span class="badge bg-danger-subtle text-danger">DS</span>' : '<span class="badge bg-primary-subtle text-primary">EX</span>';
          tr.innerHTML = `
            <td>${domBadge}</td>
            <td>${r.seq}</td>
            <td><strong>${r.term}</strong></td>
            <td>${r.stat}</td>
            <td>${r.dt || '—'}</td>
          `;
          exBody.appendChild(tr);
        });
      }
    }

    // Initialize on page load
    window.addEventListener('DOMContentLoaded', initDashboard);
  </script>

</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
