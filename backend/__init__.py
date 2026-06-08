from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env na raiz do projeto.
# Também funciona quando o backend é executado como módulo.
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)
