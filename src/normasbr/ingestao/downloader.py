from pathlib import Path

import requests
import tqdm


def download_tsv(lista_path: Path, base_path: Path):
    arquivos = []
    with open(lista_path) as f:
        for linha in f:
            nome, link = linha.split("\t", 1)
            arquivos.append((nome, link))

    for nome, link in arquivos:
        print(link, nome)
        download(nome.strip(), link.strip(), base_path)


def download(nome: str, url: str, base_path: Path):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:154.0) Gecko/20100101 Firefox/154.0"
    }
    r = requests.get(url, timeout=30, headers=headers)
    if not r.ok:
        print(
            f"Ocorreu um erro ao baixar a url {url} do arquivo {nome}: {r.status_code}"
        )

    mimetype = r.headers.get("Content-Type")

    if mimetype == "application/pdf":
        file_name = base_path / (nome + ".pdf")
        if file_name.exists():
            print(f"Arquivo {file_name!s} já existe")
            return
        with open(file_name, "wb") as file:
            file.write(r.content)
            return

    encoding = r.encoding or r.apparent_encoding or "utf-8"
    if encoding.lower() in ("iso-8859-1", "latin-1"):
        encoding = "cp1252"

    texto = r.content.decode(encoding, errors="replace")
    file_name = base_path / (nome + ".html")
    if file_name.exists():
        print(f"Arquivo {file_name!s} já existe")
        return

    with open(file_name, "w") as file:
        file.write(texto)
        return
