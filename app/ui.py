
import streamlit as st
import requests
import time

# Point this to your FastAPI server
API_BASE_URL = "http://localhost:9000/api/v1/pdf"

# Page Configuration
st.set_page_config(page_title="AI Deck Builder", page_icon="📊", layout="centered")

st.title("📊 AI-Powered PDF to PPTX Generator")
st.markdown("""
Upload a document, and our AI pipeline will extract the text, analyze the structure, 
and design a professional, industry-ready PowerPoint presentation.
""")

st.divider()

# File Uploader
uploaded_file = st.file_uploader("Upload your PDF Document", type=["pdf"])

if uploaded_file is not None:
    if st.button("Generate Presentation", type="primary", use_container_width=True):

        # ── Step 1: Upload ──────────────────────────────────────────────
        with st.spinner("Uploading document to secure storage..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            try:
                response = requests.post(f"{API_BASE_URL}/generate-async", files=files, timeout=300)
                response.raise_for_status()
                job_data = response.json()
                job_id = job_data.get("job_id")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to the backend: {e}")
                st.stop()

        st.success(f"Upload successful! Job ID: `{job_id}`")
        st.divider()

        # ── Step 2: Polling UI ──────────────────────────────────────────
        st.markdown("### ⚙️ Processing Pipeline")

        status_placeholder = st.empty()
        progress_bar = st.progress(0)

        # Also add a missing status: fetching_images
        status_map = {
            "queued":                    (5,   "⏳ Queued for processing..."),
            "downloading_from_storage":  (15,  "☁️ Retrieving from MinIO storage..."),
            "processing_text":           (30,  "📄 Extracting text and detecting structure..."),
            "generating_outline":        (55,  "🧠 AI is designing the presentation outline (this may take a minute)..."),
            "fetching_images":           (70,  "🖼️ Fetching relevant images for slides..."),
            "rendering_pptx":            (88,  "🎨 Applying design themes and drawing slides..."),
            "completed":                 (100, "✅ Presentation Ready!"),
            "failed":                    (0,   "❌ Generation Failed."),
        }

        # ── Step 3: Polling Loop ────────────────────────────────────────
        consecutive_errors = 0
        MAX_ERRORS = 5

        while True:
            try:
                status_res = requests.get(
                    f"{API_BASE_URL}/jobs/{job_id}/status",
                    timeout=30,
                )
            except requests.exceptions.RequestException:
                consecutive_errors += 1
                if consecutive_errors >= MAX_ERRORS:
                    st.error("Lost connection to the backend server after multiple retries.")
                    st.stop()
                time.sleep(3)
                continue

            consecutive_errors = 0  # reset on success

            if status_res.status_code != 200:
                st.error(f"Unexpected response from server: {status_res.status_code}")
                st.stop()

            current_job = status_res.json()
            current_status = current_job.get("status", "queued")

            progress_val, friendly_text = status_map.get(
                current_status, (0, f"🔄 {current_status}...")
            )

            progress_bar.progress(progress_val)

            # ── Completed ──
            if current_status == "completed":
                status_placeholder.success(f"**Status:** {friendly_text}")
                result = current_job.get("result", {})

                st.divider()
                st.markdown("### 🎉 Generation Complete!")

                doc_title = result.get("document_title", "Your Presentation")
                st.write(f"**Document Detected:** {doc_title}")

                download_path = result.get("download_url", "")

                if download_path:
                    # Fix: use the same port as API_BASE_URL (9000), not hardcoded 8000
                    full_download_url = f"http://localhost:9000{download_path}"

                    # Native Streamlit download button (fetches file as bytes)
                    try:
                        file_response = requests.get(full_download_url, timeout=60)
                        file_response.raise_for_status()

                        st.download_button(
                            label="📥 Download .PPTX Presentation",
                            data=file_response.content,
                            file_name=f"{doc_title.replace(' ', '_')}.pptx",
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            use_container_width=True,
                        )
                    except requests.exceptions.RequestException as e:
                        # Fallback to HTML link if fetch fails
                        st.warning("Could not fetch file directly. Use the link below:")
                        st.markdown(
                            f"""
                            <a href="{full_download_url}" target="_blank" style="text-decoration:none;">
                                <button style="background-color:#FF4B4B;color:white;padding:12px 24px;
                                border:none;border-radius:6px;cursor:pointer;width:100%;
                                font-size:16px;font-weight:bold;">
                                    📥 Download .PPTX Presentation
                                </button>
                            </a>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.error("Download URL not found in response.")

                break

            # ── Failed ──
            elif current_status == "failed":
                error_detail = current_job.get("error", "Unknown error occurred.")
                status_placeholder.error(f"**Generation Failed:** {error_detail}")
                st.code(error_detail, language="text")
                break

            # ── Still Processing ──
            else:
                status_placeholder.info(f"**Status:** {friendly_text}")
                time.sleep(2)