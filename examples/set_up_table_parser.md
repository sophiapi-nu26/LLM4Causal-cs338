============================================================
Installation Guide: Ollama + Docling
============================================================

1. Install Ollama (no sudo required)
------------------------------------

Ollama provides prebuilt .tar.gz releases you can unpack
directly into your home directory.

Step 1. Download the latest release:
    wget https://github.com/ollama/ollama/releases/download/v0.3.7/ollama-linux-amd64.tgz

Step 2. Extract to your home directory:
    tar -xvzf ollama-linux-amd64.tgz -C $HOME

Step 3. Add Ollama to your PATH
   (append this line to ~/.bashrc or ~/.zshrc):
    export PATH=$HOME/ollama/bin:$PATH

Step 4. Reload your shell:
    source ~/.bashrc


2. Install Docling (via Conda, recommended)
--------------------------------------------

Docling requires Python with lzma support,
which is included in Conda’s prebuilt binaries.

Step 1. Create or activate a Conda environment with Python 3.12:
    conda create -n docling_env -c conda-forge python=3.12 -y
    conda activate docling_env

Step 2. Install Docling and dependencies:
    pip install docling pandas


============================================================
You now have Ollama installed (binary available on PATH)
and Docling installed inside a Conda environment.
============================================================
