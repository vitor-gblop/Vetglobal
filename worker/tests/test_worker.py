import asyncio

from src.main.workers.worker import Worker


def test_worker_sends_deterministic_summary_callback():
    # Guarda as mensagens que o worker enviaria para a API.
    received = []

    async def callback(payload):
        # Simula o endpoint de callback armazenando o payload recebido.
        received.append(payload)

    # Executa o worker sem IA e aguarda a coroutine terminar.
    summary = asyncio.run(
        Worker(callback=callback).start(
            "Nome do pet: Luna\nIdade: 4",
            job_id=7,
            document_id=11,
        )
    )

    # Valida o resumo e os metadados enviados no callback de sucesso.
    assert "Paciente: Luna" in summary
    assert received[0]["status"] == "DONE"
    assert received[0]["job_id"] == 7
    assert received[0]["document_id"] == 11


def test_worker_uses_ai_summary(monkeypatch):
    # Importa o módulo para substituir a chamada externa ao Gemini.
    from src.main.workers import worker as worker_module

    # Registra o texto que seria enviado ao modelo de IA.
    calls = []

    def fake_summarize(text):
        # Retorna uma resposta fixa sem depender da API do Google.
        calls.append(text)
        return "Resumo gerado por IA"

    # Intercepta summarize_text apenas durante este teste.
    monkeypatch.setattr(worker_module, "summarize_text", fake_summarize)

    # Executa o worker solicitando o caminho de sumarização por IA.
    summary = asyncio.run(
        Worker().start(
            "Nome do pet: Luna\nIdade: 4",
            job_id=8,
            use_ai=True,
        )
    )

    # Confirma a resposta simulada e o texto recebido pela IA.
    assert summary == "Resumo gerado por IA"
    assert calls == ["Nome do pet: Luna\nIdade: 4"]
