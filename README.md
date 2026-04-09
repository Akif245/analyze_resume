# Resume Analyzer

This folder now contains both:

- a Python CLI for strict JSON analysis
- a local browser UI for uploading resumes and viewing results in a cleaner dashboard

## Files

- `analyzer.py` - Main resume analyzer script
- `app.py` - Local web UI with resume upload and structured result cards
- `TASKS_AND_CHANGES.txt` - Plain-text log of completed work and changes

## Run The UI

Start the local app:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

Custom host or port:

```powershell
python app.py --host 127.0.0.1 --port 8001
```

The app also reads `HOST` and `PORT` environment variables automatically, which makes it deployment-friendly for Render.

## Run The CLI

Analyze a resume from a file:

```powershell
python analyzer.py --resume-file resume.txt
```

Analyze a resume and compare it with a job description:

```powershell
python analyzer.py --resume-file resume.txt --jd-file jd.txt
```

Save output to a file:

```powershell
python analyzer.py --resume-file resume.txt --jd-file jd.txt --output result.json
```

Pass direct text instead of files:

```powershell
python analyzer.py --resume-text "John Doe`nEmail: john@example.com" --jd-text "Looking for a Python developer"
```

## Notes

- Output follows the strict JSON structure requested.
- Empty resumes return an error JSON.
- Short or incomplete resumes are still analyzed, but confidence is reduced and warnings are added.
- Skill inference is heuristic-based and avoids unsupported claims.
- Upload UI supports pasted text and file uploads.
- File upload supports `.txt` and `.docx` directly.
- `.pdf` support is enabled if you install the optional dependency:

```powershell
pip install pypdf
```

## Deploy On Render

This project is now prepared for Render deployment.

Files added for deployment:

- `requirements.txt`
- `render.yaml`

Basic Render flow:

1. Push this project to GitHub.
2. In Render, create a new web service from the GitHub repo.
3. Render can detect `render.yaml`, or you can manually use:

```text
Build Command: pip install -r requirements.txt
Start Command: python app.py --host 0.0.0.0 --port $PORT
```

4. Deploy and open the generated Render URL.

Notes:

- The app uses local in-memory processing only and does not require a database.
- PDF upload works in deployment because `pypdf` is included in `requirements.txt`.
