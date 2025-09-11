import subprocess
import time
import requests
import argparse
from pathlib import Path
from lxml import etree

DOCKER_IMAGE = "grobid/grobid:0.8.2-crf"
HOST_PORT = "8070"
CONTAINER_PORT = "8070"

def launch_grobid():
    """
    Launch GROBID container in detached mode.
    Returns the container ID if successful.
    """
    cmd = [
        "docker", "run",
        "--rm",
        "--init",
        "--ulimit", "core=0",
        "-d",  # detached mode
        "-p", f"{HOST_PORT}:{CONTAINER_PORT}",
        DOCKER_IMAGE
    ]
    try:
        container_id = subprocess.check_output(cmd, text=True).strip()
        print(f"GROBID launched in detached mode (container ID: {container_id})")
        print(f"Access it at: http://localhost:{HOST_PORT}")
        return container_id
    except subprocess.CalledProcessError as e:
        print("Failed to launch GROBID:", e)
        return None


def stop_grobid(container_id):
    """
    Stop the given GROBID container.
    """
    try:
        subprocess.run(["docker", "stop", container_id], check=True)
        print(f"⏹ GROBID container {container_id} stopped.")
    except subprocess.CalledProcessError as e:
        print("Failed to stop GROBID:", e)


def is_grobid_running(container_id):
    """
    Check if the given container ID is still running.
    Returns True if running, False otherwise.
    """
    try:
        output = subprocess.check_output(
            ["docker", "ps", "-q", "-f", f"id={container_id}"],
            text=True
        ).strip()
        return bool(output)
    except subprocess.CalledProcessError:
        return False

def wait_until_alive(grobid_url, timeout_s=90):
    """Poll /api/isalive until it returns 200 'true' or timeout."""
    url = f"{grobid_url.rstrip('/')}/api/isalive"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = requests.get(url, timeout=3)
            if r.ok and (r.text or "").strip().lower() == "true":
                print("GROBID is alive ✅")
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    print("Timed out waiting for GROBID to be ready.")
    return False

def call_grobid(pdf_path, grobid_url):
    endpoint = f"{grobid_url.rstrip('/')}/api/processFulltextDocument"
    files = {"input": open(pdf_path, "rb")}
    data = {
        "consolidateCitations": "1",
        "teiCoordinates": "biblStruct,ref,figure,figDesc,table"
    }
    resp = requests.post(endpoint, files=files, data=data, timeout=120)
    resp.raise_for_status()
    return resp.content

def extract_text(root):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    paras = root.xpath("//tei:text/tei:body//tei:p", namespaces=ns)
    return "\n\n".join(" ".join(p.itertext()).strip() for p in paras if p.text or list(p))

#-----------------------
# run extraction
#-----------------------
def run_extraction(args):
    """
    Run extraction using GROBID.
    """
    tei_bytes = call_grobid(args.pdf, args.grobid_url)
    (args.outdir / "fulltext.tei.xml").write_bytes(tei_bytes)

    root = etree.fromstring(tei_bytes)

    (args.outdir / "text.txt").write_text(extract_text(root), encoding="utf-8")

# Example usage
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="../tests/data/sciadv.abo6043.pdf",help="Path to local PDF file")
    parser.add_argument("--grobid-url", default="http://localhost:8070", help="Base GROBID URL")
    parser.add_argument("--outdir", default="./temp/text", help="Output directory")
    args = parser.parse_args()

    args.outdir = Path(args.outdir)
    args.outdir.mkdir(parents=True, exist_ok=True)
    # launch grobid
    cid = launch_grobid()
    if cid is None:
        print("Could not launch GROBID. Exiting.")
        return
    try:
        if not wait_until_alive(args.grobid_url, timeout_s=120):
            print("GROBID not ready. Exiting.")
            return

        run_extraction(args)
    finally:
        stop_grobid(cid)

if __name__ == "__main__":
    main()

