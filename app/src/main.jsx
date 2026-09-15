import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";

import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [pet, setPet] = useState({
    name: "",
    owner_name: "",
    species: "",
    age: "",
  });
  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState("UNIQUE");
  const [useAi, setUseAi] = useState(false);
  const [job, setJob] = useState(null);
  const [document, setDocument] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function updatePet(event) {
    setPet({ ...pet, [event.target.name]: event.target.value });
  }

  async function createPet(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);

    try {
      // A API valida o payload Pydantic e devolve o ID usado no upload.
      const response = await fetch(`${API_URL}/pets/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...pet, age: Number(pet.age) }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const createdPet = await response.json();
      setPet((current) => ({ ...current, id: createdPet.id }));
      setMessage(`Pet criado com ID ${createdPet.id}. Agora envie um documento.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadDocument(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!pet.id) {
      setError("Crie o pet antes de enviar um documento.");
      return;
    }
    if (!file) {
      setError("Selecione um arquivo TXT ou PDF.");
      return;
    }

    setBusy(true);
    try {
      // FormData preserva o arquivo e o campo document_type do endpoint FastAPI.
      const formData = new FormData();
      formData.append("document_type", documentType);
      formData.append("file", file);

      const path = useAi
        ? `/pets/${pet.id}/documents/ai`
        : `/pets/${pet.id}/documents`;
      const response = await fetch(`${API_URL}${path}`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error(await readError(response));

      const createdJob = await response.json();
      setJob(createdJob);
      setDocument(null);
      setMessage(`Job ${createdJob.job_id} enfileirado. Aguardando o worker...`);
      pollJob(createdJob.document_id, createdJob.job_id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function pollJob(documentId, jobId) {
    try {
      // O endpoint faz long-polling; uma nova chamada só ocorre após uma resposta.
      const response = await fetch(
        `${API_URL}/documents/${documentId}/poll?after_job_id=${jobId - 1}`,
      );
      if (response.status === 204) {
        pollJob(documentId, jobId);
        return;
      }
      if (!response.ok) throw new Error(await readError(response));

      const result = await response.json();
      setDocument(result);
      setJob((current) => ({ ...current, status: "DONE" }));
      setMessage("Processamento concluído.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">VetGlobal</p>
        <h1>Documentos clínicos de pets</h1>
        <p className="subtitle">
          Crie um pet, envie o documento e acompanhe o processamento assíncrono.
        </p>
      </section>

      <section className="grid">
        <form className="card" onSubmit={createPet}>
          <h2>1. Criar pet</h2>
          <label>
            Nome
            <input name="name" value={pet.name} onChange={updatePet} required />
          </label>
          <label>
            Tutor
            <input
              name="owner_name"
              value={pet.owner_name}
              onChange={updatePet}
              required
            />
          </label>
          <label>
            Espécie/raça
            <input
              name="species"
              value={pet.species}
              onChange={updatePet}
              required
            />
          </label>
          <label>
            Idade
            <input
              name="age"
              type="number"
              min="0"
              value={pet.age}
              onChange={updatePet}
              required
            />
          </label>
          <button disabled={busy} type="submit">
            Criar pet
          </button>
          {pet.id && <span className="success">Pet atual: #{pet.id}</span>}
        </form>

        <form className="card" onSubmit={uploadDocument}>
          <h2>2. Enviar documento (pet {pet.id})</h2>
          <label>
            Tipo do documento
            <select
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value)}
            >
              <option value="UNIQUE">Único (sobrescreve o anterior)</option>
              <option value="MULTIPLE">Múltiplo (mantém históricos)</option>
            </select>
          </label>
          <label>
            Arquivo TXT ou PDF
            <input
              type="file"
              accept=".txt,.pdf,text/plain,application/pdf"
              onChange={(event) => setFile(event.target.files[0] || null)}
              required
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={useAi}
              onChange={(event) => setUseAi(event.target.checked)}
            />
            Sumarizar com IA
          </label>
          <button disabled={busy || !pet.id} type="submit">
            Enviar para processamento
          </button>
        </form>
      </section>

      <section className="card status-card">
        <h2>3. Status do worker</h2>
        {job ? (
          <div className="status-content">
            <span className={`badge ${job.status.toLowerCase()}`}>
              {job.status}
            </span>
            <span>Job #{job.job_id}</span>
            <span>Documento #{job.document_id}</span>
          </div>
        ) : (
          <p>Nenhum job enviado ainda.</p>
        )}
        {document?.summary && (
          <article className="summary">
            <h3>Resumo</h3>
            <p>{document.summary}</p>
          </article>
        )}
      </section>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="notice error">{error}</p>}
    </main>
  );
}

async function readError(response) {
  try {
    const body = await response.json();
    return body.detail || "A API recusou a operação.";
  } catch {
    return `Erro HTTP ${response.status}`;
  }
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
