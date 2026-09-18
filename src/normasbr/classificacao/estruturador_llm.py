# pyright: reportAny=false
# pyright: reportExplicitAny=false
# pyright: reportUnknownVariableType=false

# Preciso ignorar alguns tipos, pois internamente lido com muitos Any e Unknown.

import json
import random
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

import requests
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass()
class EstruturadorDadosLLM(Generic[T]):
    template_prompt: str
    estrutura_esperada: type[T]
    url: str
    modelo: str
    token_acesso: str | None = None
    n_tentativas: int = 20
    delay_base_tentativa: int = 5
    timeout_conecao: int = 10
    timeout_resposta: int = 30
    cache: Path | None = Path.home() / ".cache" / "normasbr.db"

    def __call__(self, *args: Any, **kwds: Any) -> T:
        prompt = self.template_prompt.format(*args, **kwds)

        payload: dict[str, Any] = {
            "model": self.modelo,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "resposta",
                    "schema": self.obter_json_schema(),
                },
            },
            "stream": False,
            "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": False},
            "reasoning": {
                "enabled": False,
            },
        }

        if self.cache:
            resultado_bruto = _cachear_sqlite(
                self.cache, json.dumps(payload), lambda: self.__obter_resultado(payload)
            )
        else:
            resultado_bruto = self.__obter_resultado(payload)

        return self.estrutura_esperada.model_validate(json.loads(resultado_bruto))

    def obter_json_schema(self):
        return self.__simplificar_schema(self.estrutura_esperada.model_json_schema())

    def __obter_resultado(self, payload: dict[str, Any]) -> str:
        resposta = self.__tentar_realizar_request(payload)
        return str(
            resposta.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        )

    def __tentar_realizar_request(self, payload: dict[str, Any]):
        for tentativa in range(self.n_tentativas):
            try:
                session = requests.Session()
                session.trust_env = True

                if self.token_acesso:
                    session.headers.update(
                        {"Authorization": f"Bearer {self.token_acesso}"}
                    )

                resposta = session.post(
                    self.url,
                    json=payload,
                    timeout=(self.timeout_conecao, self.timeout_resposta),
                )

                resposta.raise_for_status()
                return resposta.json()

            except (
                requests.Timeout,
                requests.ConnectionError,
                requests.HTTPError,
                requests.JSONDecodeError,
            ) as e:
                if tentativa == self.n_tentativas - 1:
                    # Evitando um delay desnecessário na ultima tentativa
                    break

                delay = self.delay_base_tentativa * (2**tentativa - 1)
                # jitter aleatório para evitar thundering herd
                delay += random.uniform(0, 5)

                print(
                    f"Tentativa {tentativa + 1} falhou: {e}. Retry em {delay:.2f}s..."
                )

                time.sleep(delay)
        raise Exception("Não foi possível realizar a requisição.")

    def __simplificar_schema(self, schema: Any) -> dict[str, Any] | list[Any]:
        if isinstance(schema, dict):
            return {
                k: self.__simplificar_schema(v)
                for k, v in schema.items()
                if k
                not in {
                    "title",
                    "default",
                    "examples",
                    "$defs",
                    "description",
                }
            }

        if isinstance(schema, list):
            return [self.__simplificar_schema(v) for v in schema]

        return schema


def _cachear_sqlite(path: Path, entrada: str, executor: Callable[[], str]):
    with sqlite3.connect(path) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS prompt_cache (id int, entrada text, resultado text);"
        )
        res = cur.execute(
            "SELECT resultado FROM prompt_cache WHERE entrada = ?;", (entrada,)
        ).fetchmany(1)

        if len(res) and res[0]:
            return res[0][0]  # Linha 0, atributo 0

        res = executor()
        cur.execute(
            "INSERT INTO prompt_cache(id, entrada, resultado) VALUES (?, ?, ?);",
            (time.time_ns(), entrada, res),
        ).fetchone()
        return res
