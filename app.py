import argparse
import cgi
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from analyzer import analyze_resume, analyze_resume_file_bytes


def page_template(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resume Analyzer</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --panel: rgba(255, 251, 245, 0.88);
      --panel-strong: #fffaf2;
      --ink: #1f2937;
      --muted: #5f6b7a;
      --line: rgba(120, 98, 72, 0.18);
      --accent: #b45309;
      --accent-deep: #7c2d12;
      --success: #166534;
      --warn: #9a3412;
      --danger: #991b1b;
      --shadow: 0 18px 45px rgba(84, 54, 24, 0.12);
      --radius: 24px;
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(250, 204, 21, 0.24), transparent 32%),
        radial-gradient(circle at top right, rgba(234, 88, 12, 0.16), transparent 28%),
        linear-gradient(180deg, #fbf6ee 0%, #f2e9db 100%);
      min-height: 100vh;
    }}

    .wrap {{
      width: 100%;
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 16px 56px;
    }}

    .hero {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 20px;
      align-items: stretch;
      margin-bottom: 24px;
      width: 100%;
    }}

    .hero-card, .panel, .result-card {{
      background: var(--panel);
      backdrop-filter: blur(10px);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}

    .hero-copy {{
      padding: 28px;
    }}

    .eyebrow {{
      display: inline-block;
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--accent-deep);
      margin-bottom: 12px;
    }}

    h1 {{
      margin: 0 0 10px;
      font-size: clamp(32px, 5vw, 54px);
      line-height: 0.95;
      font-family: Georgia, "Times New Roman", serif;
    }}

    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.6;
      max-width: 60ch;
    }}

    .hero-stats {{
      padding: 24px;
      display: grid;
      gap: 14px;
      align-content: center;
    }}

    .stat {{
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
    }}

    .stat strong {{
      display: block;
      font-size: 28px;
      margin-bottom: 4px;
      color: var(--accent-deep);
    }}

    .grid {{
      display: grid;
      grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
      gap: 20px;
      align-items: start;
      width: 100%;
      min-width: 0;
    }}

    .panel {{
      padding: 22px;
      position: sticky;
      top: 20px;
      min-width: 0;
    }}

    .panel h2, .results h2 {{
      margin: 0 0 14px;
      font-size: 20px;
    }}

    label {{
      display: block;
      margin: 14px 0 8px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--accent-deep);
    }}

    textarea, input[type="file"] {{
      width: 100%;
      border: 1px solid rgba(120, 98, 72, 0.22);
      background: rgba(255, 255, 255, 0.72);
      border-radius: 16px;
      padding: 14px 16px;
      font: inherit;
      color: var(--ink);
    }}

    textarea {{
      min-height: 170px;
      resize: vertical;
    }}

    .hint {{
      font-size: 13px;
      color: var(--muted);
      margin-top: 8px;
      line-height: 1.5;
    }}

    .actions {{
      display: flex;
      gap: 12px;
      margin-top: 18px;
      flex-wrap: wrap;
    }}

    button {{
      border: 0;
      border-radius: 999px;
      padding: 13px 20px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      color: white;
      background: linear-gradient(135deg, var(--accent), var(--accent-deep));
      box-shadow: 0 10px 26px rgba(180, 83, 9, 0.28);
    }}

    .ghost {{
      display: inline-flex;
      align-items: center;
      padding: 13px 18px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--ink);
      text-decoration: none;
      background: rgba(255, 255, 255, 0.55);
    }}

    .results {{
      display: grid;
      gap: 18px;
      min-width: 0;
    }}

    .result-card {{
      padding: 22px;
    }}

    .score-band {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}

    .metric {{
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
    }}

    .metric .value {{
      font-size: 32px;
      font-weight: 800;
      margin-bottom: 6px;
      overflow-wrap: anywhere;
    }}

    .muted {{
      color: var(--muted);
      line-height: 1.6;
      overflow-wrap: anywhere;
    }}

    .chips {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }}

    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(180, 83, 9, 0.1);
      color: var(--accent-deep);
      font-size: 13px;
      font-weight: 700;
      max-width: 100%;
      overflow-wrap: anywhere;
    }}

    .section-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      min-width: 0;
    }}

    .list {{
      margin: 12px 0 0;
      padding-left: 18px;
      line-height: 1.65;
    }}

    .item-block {{
      padding: 16px 0;
      border-top: 1px solid var(--line);
    }}

    .item-block:first-child {{
      border-top: 0;
      padding-top: 0;
    }}

    .item-title {{
      font-weight: 800;
      margin-bottom: 4px;
      overflow-wrap: anywhere;
    }}

    .item-subtitle {{
      color: var(--muted);
      margin-bottom: 8px;
      overflow-wrap: anywhere;
    }}

    pre {{
      margin: 0;
      padding: 18px;
      overflow-x: auto;
      overflow-y: auto;
      max-width: 100%;
      border-radius: 18px;
      background: #1b1f24;
      color: #e5edf5;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .banner {{
      padding: 14px 16px;
      border-radius: 16px;
      margin-bottom: 18px;
      line-height: 1.5;
      border: 1px solid transparent;
    }}

    .banner.error {{
      background: rgba(239, 68, 68, 0.1);
      color: var(--danger);
      border-color: rgba(239, 68, 68, 0.18);
    }}

    .banner.info {{
      background: rgba(22, 101, 52, 0.08);
      color: var(--success);
      border-color: rgba(22, 101, 52, 0.12);
    }}

    .footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
      text-align: center;
    }}

    @media (max-width: 1180px) {{
      .grid {{
        grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
      }}
    }}

    @media (max-width: 980px) {{
      .hero, .grid, .section-grid, .score-band {{
        grid-template-columns: 1fr;
      }}

      .panel {{
        position: static;
      }}

      .hero-copy, .hero-stats, .panel, .result-card {{
        padding: 20px;
      }}
    }}

    @media (max-width: 640px) {{
      .wrap {{
        max-width: 100%;
        padding: 18px 10px 40px;
      }}

      .hero {{
        gap: 14px;
        margin-bottom: 16px;
      }}

      h1 {{
        font-size: clamp(28px, 10vw, 40px);
        line-height: 1;
      }}

      .hero p {{
        font-size: 15px;
      }}

      .hero-copy, .hero-stats, .panel, .result-card {{
        padding: 16px;
        border-radius: 20px;
      }}

      .panel,
      .results,
      .result-card,
      .metric,
      .section-grid > div,
      .item-block {{
        min-width: 0;
      }}

      .stat strong {{
        font-size: 22px;
      }}

      textarea {{
        min-height: 140px;
      }}

      .actions {{
        flex-direction: column;
      }}

      button, .ghost {{
        width: 100%;
        justify-content: center;
      }}

      .metric {{
        padding: 14px;
      }}

      .metric .value {{
        font-size: 26px;
      }}

      .chips {{
        gap: 6px;
      }}

      .chip {{
        width: 100%;
        border-radius: 14px;
        justify-content: center;
        text-align: center;
      }}

      pre {{
        padding: 14px;
        font-size: 12px;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-card hero-copy">
        <span class="eyebrow">Recruiter Dashboard</span>
        <h1>Resume Analyzer</h1>
        <p>Upload a resume, optionally paste the target job description, and review ATS score, strengths, gaps, projects, and role fit in a cleaner format.</p>
      </div>
      <div class="hero-card hero-stats">
        <div class="stat"><strong>TXT / DOCX / PDF</strong><span class="muted">Upload common resume formats. PDF extraction needs <code>pypdf</code>.</span></div>
        <div class="stat"><strong>Structured Review</strong><span class="muted">Readable cards on the page plus raw JSON at the bottom.</span></div>
        <div class="stat"><strong>Local Only</strong><span class="muted">Everything runs on your machine at <code>localhost</code>.</span></div>
      </div>
    </section>
    {content}
    <div class="footer">Built for local resume screening and recruiter-style review.</div>
  </div>
</body>
</html>"""


def chip_list(values) -> str:
    if not values:
        return '<div class="muted">None detected.</div>'
    return '<div class="chips">' + "".join(
        f'<span class="chip">{html.escape(str(value))}</span>' for value in values
    ) + "</div>"


def bullet_list(values) -> str:
    if not values:
        return '<div class="muted">No items available.</div>'
    return '<ul class="list">' + "".join(f"<li>{html.escape(str(value))}</li>" for value in values) + "</ul>"


def render_experience(items) -> str:
    if not items:
        return '<div class="muted">No clear experience entries were extracted.</div>'
    blocks = []
    for item in items:
        contributions = bullet_list(item.get("key_contributions", []))
        blocks.append(
            f"""
            <div class="item-block">
              <div class="item-title">{html.escape(str(item.get("role") or "Unknown Role"))}</div>
              <div class="item-subtitle">{html.escape(str(item.get("company") or "Unknown Company"))} • {html.escape(str(item.get("duration") or "Duration not found"))}</div>
              {contributions}
            </div>
            """
        )
    return "".join(blocks)


def render_projects(items) -> str:
    if not items:
        return '<div class="muted">No clear projects were detected.</div>'
    blocks = []
    for item in items:
        tech_stack = chip_list(item.get("tech_stack", []))
        blocks.append(
            f"""
            <div class="item-block">
              <div class="item-title">{html.escape(str(item.get("project_name") or "Unnamed Project"))}</div>
              <div class="item-subtitle">Complexity: {html.escape(str(item.get("complexity_level") or "Unknown"))} • Impact: {html.escape(str(item.get("real_world_impact") or "Unknown"))}</div>
              <div class="muted">{html.escape(str(item.get("problem_solved") or ""))}</div>
              {tech_stack}
            </div>
            """
        )
    return "".join(blocks)


def render_education(items) -> str:
    if not items:
        return '<div class="muted">No clear education entries were extracted.</div>'
    blocks = []
    for item in items:
        blocks.append(
            f"""
            <div class="item-block">
              <div class="item-title">{html.escape(str(item.get("degree") or "Degree not found"))}</div>
              <div class="item-subtitle">{html.escape(str(item.get("institution") or "Institution not found"))} • {html.escape(str(item.get("year") or "Year not found"))}</div>
            </div>
            """
        )
    return "".join(blocks)


def render_result(result: dict) -> str:
    if result.get("error"):
        return f'<div class="banner error">{html.escape(result["error"])}</div>'

    basic_info = result.get("basic_info", {})
    experience = result.get("experience", {})
    projects = result.get("projects", {})
    education = result.get("education", {})
    ats_score = result.get("ats_score", {})
    job_match = result.get("job_match", {})
    final_verdict = result.get("final_verdict", {})

    return f"""
    <div class="results">
      <div class="result-card">
        <h2>Overview</h2>
        <div class="score-band">
          <div class="metric">
            <div class="value">{html.escape(str(ats_score.get("score", 0)))}</div>
            <div class="muted">ATS Score</div>
          </div>
          <div class="metric">
            <div class="value">{html.escape(str(job_match.get("match_percentage") if job_match.get("match_percentage") is not None else "N/A"))}</div>
            <div class="muted">Job Match %</div>
          </div>
          <div class="metric">
            <div class="value">{html.escape(str(final_verdict.get("hireability_level", "N/A")))}</div>
            <div class="muted">Hireability</div>
          </div>
        </div>
        <div class="muted">{html.escape(str(ats_score.get("reason", "")))}</div>
      </div>

      <div class="result-card">
        <h2>Candidate Snapshot</h2>
        <div class="section-grid">
          <div>
            <div class="item-title">{html.escape(str(basic_info.get("full_name") or "Name not found"))}</div>
            <div class="item-subtitle">{html.escape(str(basic_info.get("location") or "Location not found"))}</div>
            {chip_list([
              basic_info.get("email"),
              basic_info.get("phone"),
              basic_info.get("linkedin"),
              basic_info.get("github_portfolio"),
            ])}
          </div>
          <div>
            <div class="item-title">Suitable Roles</div>
            {chip_list(final_verdict.get("suitable_roles", []))}
            <div class="item-subtitle" style="margin-top: 12px;">Confidence: {html.escape(str(final_verdict.get("confidence_level", "Unknown")))}</div>
          </div>
        </div>
      </div>

      <div class="result-card">
        <h2>Skills</h2>
        <div class="section-grid">
          <div><div class="item-title">Programming Languages</div>{chip_list(result.get("skills", {}).get("Programming Languages", []))}</div>
          <div><div class="item-title">Frameworks / Libraries</div>{chip_list(result.get("skills", {}).get("Frameworks/Libraries", []))}</div>
          <div><div class="item-title">Tools / Technologies</div>{chip_list(result.get("skills", {}).get("Tools/Technologies", []))}</div>
          <div><div class="item-title">Databases</div>{chip_list(result.get("skills", {}).get("Databases", []))}</div>
        </div>
        <div style="margin-top: 14px;"><div class="item-title">Soft Skills</div>{chip_list(result.get("skills", {}).get("Soft Skills", []))}</div>
      </div>

      <div class="result-card">
        <h2>Experience</h2>
        <div class="item-subtitle">Total experience: {html.escape(str(experience.get("total_experience", "0 years 0 months")))}</div>
        {render_experience(experience.get("items", []))}
        <div style="margin-top: 12px;">
          <div class="item-title">Career Gaps</div>
          {bullet_list(experience.get("career_gaps", []))}
        </div>
      </div>

      <div class="result-card">
        <h2>Projects</h2>
        <div class="section-grid">
          <div>
            <div class="item-title">Best Project</div>
            <div class="item-subtitle">{html.escape(str(projects.get("best_project") or "Not identified"))}</div>
          </div>
          <div>
            <div class="item-title">Weak / Repetitive Projects</div>
            {chip_list(projects.get("weak_or_repetitive_projects", []))}
          </div>
        </div>
        {render_projects(projects.get("items", []))}
      </div>

      <div class="result-card">
        <h2>Education</h2>
        {render_education(education.get("items", []))}
      </div>

      <div class="result-card">
        <h2>Strengths and Weaknesses</h2>
        <div class="section-grid">
          <div>
            <div class="item-title">Strengths</div>
            {bullet_list(result.get("strengths", []))}
          </div>
          <div>
            <div class="item-title">Weaknesses</div>
            {bullet_list(result.get("weaknesses", []))}
          </div>
        </div>
      </div>

      <div class="result-card">
        <h2>Job Match and Red Flags</h2>
        <div class="section-grid">
          <div>
            <div class="item-title">Matching Skills</div>
            {chip_list(job_match.get("matching_skills", []))}
            <div class="item-title" style="margin-top: 14px;">Missing Skills</div>
            {chip_list(job_match.get("missing_skills", []))}
          </div>
          <div>
            <div class="item-title">Red Flags</div>
            {bullet_list(result.get("red_flags", []))}
          </div>
        </div>
      </div>

      <div class="result-card">
        <h2>Suggestions</h2>
        {bullet_list(result.get("suggestions", []))}
      </div>

      <div class="result-card">
        <h2>Raw JSON</h2>
        <pre>{html.escape(json.dumps(result, indent=2, ensure_ascii=True))}</pre>
      </div>
    </div>
    """


def render_home(result: dict | None = None, message: str = "", error: str = "") -> str:
    banner = ""
    if error:
        banner = f'<div class="banner error">{html.escape(error)}</div>'
    elif message:
        banner = f'<div class="banner info">{html.escape(message)}</div>'

    result_markup = render_result(result) if result else """
      <div class="result-card">
        <h2>How To Use</h2>
        <div class="muted">
          1. Upload a resume file or paste resume text.<br>
          2. Optionally paste a target job description.<br>
          3. Click analyze to get a structured recruiter-style breakdown.<br><br>
          Supported upload formats: <strong>.txt</strong>, <strong>.docx</strong>, and <strong>.pdf</strong> if <code>pypdf</code> is installed.
        </div>
      </div>
    """

    content = f"""
    <div class="grid">
      <form class="panel" method="post" enctype="multipart/form-data">
        <h2>Analyze Resume</h2>
        {banner}
        <label for="resume_file">Upload Resume</label>
        <input id="resume_file" type="file" name="resume_file" accept=".txt,.docx,.pdf">
        <div class="hint">You can upload a file, paste text below, or use both. If both are present, the uploaded file is used.</div>

        <label for="resume_text">Resume Text</label>
        <textarea id="resume_text" name="resume_text" placeholder="Paste resume text here if you do not want to upload a file."></textarea>

        <label for="job_description">Job Description</label>
        <textarea id="job_description" name="job_description" placeholder="Optional: paste the target JD here for a match analysis."></textarea>

        <div class="actions">
          <button type="submit">Analyze Resume</button>
          <a class="ghost" href="/">Reset</a>
        </div>
      </form>

      {result_markup}
    </div>
    """
    return page_template(content)


class ResumeAppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.respond_html(render_home())

    def do_POST(self) -> None:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )

        uploaded = form["resume_file"] if "resume_file" in form else None
        resume_text = form.getfirst("resume_text", "")
        job_description = form.getfirst("job_description", "")

        try:
            if uploaded is not None and getattr(uploaded, "filename", ""):
                raw_bytes = uploaded.file.read()
                result = analyze_resume_file_bytes(raw_bytes, uploaded.filename, job_description)
                page = render_home(result=result, message=f"Analysis completed for {uploaded.filename}.")
            elif resume_text.strip():
                result = analyze_resume(resume_text, job_description)
                page = render_home(result=result, message="Analysis completed from pasted resume text.")
            else:
                page = render_home(error="Please upload a resume file or paste resume text before analyzing.")
        except Exception as exc:
            page = render_home(error=str(exc))

        self.respond_html(page)

    def log_message(self, format: str, *args) -> None:
        return

    def respond_html(self, content: str) -> None:
        encoded = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Resume Analyzer web UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the local server.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the local server.")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ResumeAppHandler)
    print(f"Resume Analyzer UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
