import gradio as gr


def build_default_theme():
    try:
        return gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="sky",
            neutral_hue="slate",
        ).set(
            body_background_fill="#418fd6",
            body_background_fill_dark="#418fd6",
            body_text_color="#f8fbff",
            body_text_color_dark="#f8fbff",
            body_text_color_subdued="#dcecff",
            body_text_color_subdued_dark="#dcecff",
            background_fill_primary="rgba(18, 49, 100, 0.78)",
            background_fill_primary_dark="rgba(18, 49, 100, 0.78)",
            background_fill_secondary="rgba(14, 39, 83, 0.86)",
            background_fill_secondary_dark="rgba(14, 39, 83, 0.86)",
            block_background_fill="rgba(14, 39, 83, 0.78)",
            block_background_fill_dark="rgba(14, 39, 83, 0.78)",
            block_border_color="rgba(190, 225, 255, 0.28)",
            block_border_color_dark="rgba(190, 225, 255, 0.28)",
            block_label_text_color="#eff6ff",
            block_label_text_color_dark="#eff6ff",
            block_title_text_color="#eff6ff",
            block_title_text_color_dark="#eff6ff",
            block_info_text_color="#d6e8ff",
            block_info_text_color_dark="#d6e8ff",
            input_background_fill="rgba(8, 23, 55, 0.88)",
            input_background_fill_dark="rgba(8, 23, 55, 0.88)",
            input_background_fill_focus="rgba(11, 29, 66, 0.92)",
            input_background_fill_focus_dark="rgba(11, 29, 66, 0.92)",
            input_border_color="rgba(211, 235, 255, 0.26)",
            input_border_color_dark="rgba(211, 235, 255, 0.26)",
            input_border_color_focus="#bfe3ff",
            input_border_color_focus_dark="#bfe3ff",
            input_placeholder_color="#d3e6fb",
            input_placeholder_color_dark="#d3e6fb",
            color_accent="#7cc2ff",
            color_accent_soft="rgba(124, 194, 255, 0.18)",
            color_accent_soft_dark="rgba(124, 194, 255, 0.18)",
            link_text_color="#d9ecff",
            link_text_color_dark="#d9ecff",
            checkbox_label_text_color="#eff6ff",
            checkbox_label_text_color_dark="#eff6ff",
            accordion_text_color="#eff6ff",
            accordion_text_color_dark="#eff6ff",
            table_text_color="#eff6ff",
            table_text_color_dark="#eff6ff",
            button_primary_background_fill="#2f7fe0",
            button_primary_background_fill_dark="#2f7fe0",
            button_primary_background_fill_hover="#5daae8",
            button_primary_background_fill_hover_dark="#5daae8",
            button_primary_text_color="#f8fbff",
            button_primary_text_color_dark="#f8fbff",
            button_secondary_background_fill="rgba(14, 39, 83, 0.82)",
            button_secondary_background_fill_dark="rgba(14, 39, 83, 0.82)",
            button_secondary_text_color="#eff6ff",
            button_secondary_text_color_dark="#eff6ff",
        )
    except Exception:
        try:
            return gr.themes.Soft()
        except Exception:
            return None


CSS = """
:root {
    color-scheme: dark;
    --app-bg-start: #6baee8;
    --app-bg-mid: #418fd6;
    --app-bg-end: #2b73bf;
    --card-bg: rgba(10, 31, 72, 0.66);
    --card-border: rgba(214, 236, 255, 0.24);
    --primary-start: #2f7fe0;
    --primary-end: #7bc5ff;
    --text-strong: #f8fbff;
    --text-soft: #d8ebff;
    --surface-dark: rgba(8, 23, 55, 0.84);
    --surface-darker: rgba(7, 18, 44, 0.9);
}

body,
.gradio-container {
    background:
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.20), transparent 24%),
        radial-gradient(circle at top right, rgba(150, 214, 255, 0.30), transparent 26%),
        radial-gradient(circle at bottom left, rgba(9, 56, 110, 0.30), transparent 24%),
        linear-gradient(180deg, var(--app-bg-start) 0%, var(--app-bg-mid) 44%, var(--app-bg-end) 100%);
    color: var(--text-strong);
}

.gradio-container {
    min-height: 100vh;
}

.app-shell,
.hero-card,
.content-card,
.section-card,
.result-card,
.feature-note,
.tab-note {
    background: var(--card-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--card-border);
    box-shadow: 0 18px 60px rgba(15, 23, 42, 0.12);
    border-radius: 24px;
}

.app-shell {
    padding: 1.5rem;
    gap: 1.2rem;
}

.hero-card {
    padding: 1.75rem 1.9rem;
}

.hero-card h1,
.hero-card h2,
.hero-card p,
.hero-card li {
    color: var(--text-strong);
}

.hero-card p,
.tab-note {
    color: var(--text-soft);
}

.gradio-container,
.gradio-container .prose,
.gradio-container .prose *:not(code) {
    color: var(--text-strong);
}

#md_project {
    margin-bottom: 0;
}

#md_project h1 {
    margin: 0 0 0.65rem 0;
    font-size: 2.15rem;
    line-height: 1.1;
    letter-spacing: -0.03em;
}

#md_project p {
    margin: 0 0 1rem 0;
    max-width: 62ch;
    line-height: 1.7;
    font-size: 1.05rem;
}

#md_project ol {
    margin: 0;
    padding-left: 1.5rem;
    color: var(--text-soft);
    line-height: 1.9;
}

#md_project li {
    padding-left: 0.15rem;
}

.content-card,
.section-card,
.result-card {
    padding: 1.15rem 1.15rem 1.25rem 1.15rem;
}

.section-card {
    margin-bottom: 1rem;
}

.result-card {
    margin-top: 1rem;
}

.feature-note,
.tab-note {
    padding: 1rem 1.1rem;
    margin: 0.5rem 0 0.9rem 0;
    font-size: 0.95rem;
    line-height: 1.65;
}

.feature-note strong {
    color: var(--text-strong);
}

.gradio-container input,
.gradio-container textarea,
.gradio-container select,
.gradio-container table,
.gradio-container th,
.gradio-container td {
    color: var(--text-strong) !important;
}

.gradio-container input,
.gradio-container textarea,
.gradio-container select,
.gradio-container .form,
.gradio-container .panel,
.gradio-container .block {
    background: var(--surface-dark) !important;
    border-color: rgba(214, 236, 255, 0.22) !important;
}

.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
    color: #d3e6fb !important;
}

.gradio-container .tabs button,
.gradio-container .tab-nav button,
.gradio-container [role="tab"] {
    color: var(--text-soft) !important;
}

.gradio-container .tabs button.selected,
.gradio-container .tab-nav button.selected,
.gradio-container [role="tab"][aria-selected="true"] {
    color: var(--text-strong) !important;
    background: rgba(41, 102, 176, 0.92) !important;
}

.gradio-container .tabs button:hover,
.gradio-container .tab-nav button:hover,
.gradio-container [role="tab"]:hover {
    color: var(--text-strong) !important;
    background: rgba(58, 122, 199, 0.58) !important;
}

.gradio-container .label-wrap,
.gradio-container label,
.gradio-container legend,
.gradio-container .wrap {
    color: var(--text-strong) !important;
}

.markdown {
    margin-bottom: 0;
    padding-bottom: 0;
}

.tabs {
    margin-top: 0;
    padding-top: 0;
}

button.primary,
.primary,
.gr-button-primary {
    background: linear-gradient(135deg, var(--primary-start) 0%, var(--primary-end) 100%);
    border: 0;
    box-shadow: 0 14px 28px rgba(30, 107, 247, 0.24);
}

button.primary:hover,
.primary:hover,
.gr-button-primary:hover {
    filter: brightness(1.02);
    transform: translateY(-1px);
}

.bmc-button {
    padding: 2px 5px;
    border-radius: 5px;
    background-color: #FF813F;
    color: white;
    box-shadow: 0px 1px 2px rgba(0, 0, 0, 0.3);
    text-decoration: none;
    display: inline-block;
    font-size: 20px;
    margin: 2px;
    cursor: pointer;
    -webkit-transition: background-color 0.3s ease;
    -ms-transition: background-color 0.3s ease;
    transition: background-color 0.3s ease;
}
.bmc-button:hover,
.bmc-button:active,
.bmc-button:focus {
    background-color: #FF5633;
}

#md_project a {
  color: #0f62fe;
  text-decoration: none;
}
#md_project a:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
    .app-shell {
        padding: 0.95rem;
    }

    .hero-card,
    .content-card,
    .section-card,
    .result-card {
        border-radius: 18px;
    }

    #md_project h1 {
        font-size: 1.8rem;
    }
}
"""

MARKDOWN = """
# Whisper WebUI
Local speech-to-text and subtitle generation for files, YouTube links, and microphone input.

1. Choose an input source.
2. Adjust advanced options only when needed.
3. Generate subtitles and download the result.
"""

FILE_HELPER = """
Use this tab for local media already on disk. Upload a file or point the app at a local folder when that option is available.
"""

YOUTUBE_HELPER = """
Paste a YouTube link and the metadata will populate automatically before you run transcription.
"""

MIC_HELPER = """
Record in the browser, then transcribe the captured audio into a subtitle file.
"""

NLLB_UNAVAILABLE = """
**NLLB translation is unavailable on this machine.** Core transcription and DeepL translation remain available.
"""

DIARIZATION_UNAVAILABLE = """
**Speaker diarization is unavailable on this machine.** The web UI will still boot and core transcription remains available.
"""

BGM_UNAVAILABLE = """
**Background music removal is unavailable on this machine.** The web UI will still boot and core transcription remains available.
"""


NLLB_VRAM_TABLE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    table {
      border-collapse: collapse;
      width: 100%;
    }
    th, td {
      border: 1px solid #dddddd;
      text-align: left;
      padding: 8px;
    }
    th {
      background-color: #f2f2f2;
    }
  </style>
</head>
<body>

<details>
  <summary>VRAM usage for each model</summary>
  <table>
    <thead>
      <tr>
        <th>Model name</th>
        <th>Required VRAM</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>nllb-200-3.3B</td>
        <td>~16GB</td>
      </tr>
      <tr>
        <td>nllb-200-1.3B</td>
        <td>~8GB</td>
      </tr>
      <tr>
        <td>nllb-200-distilled-600M</td>
        <td>~4GB</td>
      </tr>
    </tbody>
  </table>
  <p><strong>Note:</strong> Be mindful of your VRAM! The table above provides an approximate VRAM usage for each model.</p>
</details>

</body>
</html>
"""
