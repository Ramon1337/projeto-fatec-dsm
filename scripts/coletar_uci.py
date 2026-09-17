"""Baixa e extrai somente os CSVs e o dicionário do pacote oficial Student Performance/UCI."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/320/student%2Bperformance.zip"
FILES = ("student-por.csv", "student-mat.csv", "student.txt")
MAX_BYTES = 10 * 1024 * 1024


def read_package(package, nested=False):
    """Nomes fixos impedem gravar caminhos fornecidos pelo ZIP; não usa extractall."""
    if len(package) > MAX_BYTES:
        raise ValueError("Pacote acima do limite de 10 MB.")
    with ZipFile(io.BytesIO(package)) as archive:
        if "student.zip" in archive.namelist() and not nested:
            if archive.getinfo("student.zip").file_size > MAX_BYTES:
                raise ValueError("Arquivo interno acima do limite.")
            return read_package(archive.read("student.zip"), nested=True)
        result = {}
        for filename in FILES:
            if archive.getinfo(filename).file_size > MAX_BYTES:
                raise ValueError("Arquivo da base acima do limite.")
            result[filename] = archive.read(filename)
        return result


def collect(destination, archive_path=None):
    destination = Path(destination)
    if archive_path is not None:
        archive_path = Path(archive_path)
        if archive_path.stat().st_size > MAX_BYTES:
            raise ValueError("Pacote acima do limite.")
        package = archive_path.read_bytes()
        acquisition = "importacao_de_pacote_local"
    else:
        request = Request(DOWNLOAD_URL, headers={"User-Agent": "projeto-fatec-dsm/2.0"})
        with urlopen(request, timeout=30) as response:
            package = response.read(MAX_BYTES + 1)
        acquisition = "download_oficial_https"
    files = read_package(package)
    metadata = {
        "fonte": "https://archive.ics.uci.edu/dataset/320/student+performance",
        "download": DOWNLOAD_URL, "doi": "https://doi.org/10.24432/C5TG7T",
        "autor": "Paulo Cortez", "referencia": "Cortez, P. (2008). Student Performance [Dataset]. UCI Machine Learning Repository.",
        "licenca": "CC BY 4.0", "licenca_url": "https://creativecommons.org/licenses/by/4.0/",
        "obtido_em_utc": datetime.now(timezone.utc).isoformat(), "modo_aquisicao": acquisition,
        "pacote_sha256": hashlib.sha256(package).hexdigest(),
        "arquivos_sha256": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }
    for filename, content in files.items():
        path = destination / filename
        if path.exists() and path.read_bytes() != content:
            raise ValueError("Já existe um arquivo bruto diferente. Use uma nova pasta de destino.")
    destination.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (destination / filename).write_bytes(content)
    (destination / "manifesto.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=ROOT / "data/raw/uci")
    parser.add_argument("--arquivo", type=Path, help="ZIP oficial já baixado, para execução offline.")
    args = parser.parse_args()
    try:
        collect(args.destino, args.arquivo)
    except (OSError, ValueError, KeyError, BadZipFile):
        print("Falha na coleta. Confira a conexão, o pacote oficial e a pasta de destino.", file=sys.stderr)
        return 1
    print(f"Base oficial extraída em {args.destino}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
