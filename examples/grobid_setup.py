#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import requests
from lxml import etree

# -----------------------
# GROBID management utils
# -----------------------

def ensure_grobid(grobid_url="http://localhost:8070", image="grobid/grobid:0.8.2"):
    """Ensure a grobid docker service is running at grobid_url."""
    health_url = f"{grobid_url.rstrip('/')}/api/isalive"
    try:
        r = requests.get(health_url, timeout=2)
        if r.status_code == 200:
            print("✔ GROBID service already running.")
            return
    except Exception:
        pass

    print("⚠ No running GROBID detected, starting Docker container...")
    # run detached container with auto-remove; map port 8070
    subprocess.Popen([
        "docker", "run", "--rm", "-d", "-p", "8070:8070", image
    ])

    # wait until /api/isalive responds
    for _ in range(60):  # up to ~60s
        try:
            r = requests.get(health_url, timeout=2)
            if r.status_code == 200:
                print("✔ GROBID is ready.")
                return
        except Exception:
            pass
        time.sleep(2)

    raise RuntimeError("Failed to start GROBID docker instance in time.")

# -----------------------
# Extraction functions
# -----------------------

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

def norm_text(el):
    return "" if el is None else " ".join(" ".join(el.itertext()).split())

def extract_text(root):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    paras = root.xpath("//tei:text/tei:body//tei:p", namespaces=ns)
    return "\n\n".join(" ".join(p.itertext()).strip() for p in paras if p.text or list(p))

def extract_figures(root):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    figs = []
    for fig in root.xpath("//tei:figure", namespaces=ns):
        figs.append({
            "label": fig.get("{http://www.w3.org/XML/1998/namespace}id") or fig.get("id") or "",
            "caption": norm_text(fig.find(".//tei:figDesc", namespaces=ns)) or norm_text(fig.find(".//tei:head", namespaces=ns)),
            "graphic_urls": [g.get("url") for g in fig.xpath(".//tei:graphic", namespaces=ns) if g.get("url")]
        })
    return figs

def extract_tables(root):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    tables = []
    for tab in root.xpath("//tei:table", namespaces=ns):
        tables.append({
            "label": tab.get("{http://www.w3.org/XML/1998/namespace}id") or tab.get("id") or "",
            "caption": norm_text(tab.find(".//tei:head", namespaces=ns)) or norm_text(tab.find(".//tei:figDesc", namespaces=ns)),
        })
    return tables

# -----------------------
# Main
# -----------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="D:\\llm4mat\\LLM4Causal\\tests\\data\\sciadv.abo6043.pdf", help="Path to local PDF file")
    parser.add_argument("--grobid-url", default="http://localhost:8070", help="Base GROBID URL")
    parser.add_argument("--outdir", default="D:\llm4mat\LLM4Causal\examples", help="Output directory")
    args = parser.parse_args()

    # 1. Ensure grobid is available (launch docker if needed)
    # ensure_grobid(args.grobid_url)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 2. Call grobid
    tei_bytes = call_grobid(args.pdf, args.grobid_url)
    (outdir / "fulltext.tei.xml").write_bytes(tei_bytes)

    # 3. Parse TEI
    root = etree.fromstring(tei_bytes)

    (outdir / "text.txt").write_text(extract_text(root), encoding="utf-8")
    (outdir / "figures.json").write_text(json.dumps(extract_figures(root), indent=2, ensure_ascii=False))
    (outdir / "tables.json").write_text(json.dumps(extract_tables(root), indent=2, ensure_ascii=False))

    print(f"Done. Results in {outdir}")

if __name__ == "__main__":
    main()
